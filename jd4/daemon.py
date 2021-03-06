from aiohttp import ClientError
from asyncio import gather, get_event_loop, sleep, shield, wait, FIRST_COMPLETED
from io import BytesIO
import time

from jd4.api import VJ4Session
from jd4.case import read_cases
from jd4.cache import cache_open, cache_invalidate
from jd4.cgroup import try_init_cgroup
from jd4.compile import build
from jd4.config import config, save_config
from jd4.log import logger
from jd4.status import STATUS_ACCEPTED, STATUS_COMPILE_ERROR, \
    STATUS_SYSTEM_ERROR, STATUS_JUDGING, STATUS_COMPILING
from jd4.crawer import *

RETRY_DELAY_SEC = 30

class CompileError(Exception):
    pass

class JudgeHandler:
    def __init__(self, session, request, ws):
        self.session = session
        self.request = request
        self.ws = ws

    async def handle(self):
        event = self.request.pop('event', None)
        if not event:
            await self.do_record()
        elif event == 'problem_data_change':
            await self.update_problem_data()
        else:
            logger.warning('Unknown event: %s', event)
        for key in self.request:
            logger.warning('Unused key in judge request: %s', key)

    async def do_record(self):
        self.tag = self.request.pop('tag')
        self.type = self.request.pop('type')
        self.domain_id = self.request.pop('domain_id')
        self.pid = self.request.pop('pid')
        self.rid = self.request.pop('rid')
        self.lang = self.request.pop('lang')
        self.code = self.request.pop('code')
        self.remote = self.request.pop('remote')
        try:
            if self.type == 0:
                if self.remote==False:
                    await self.do_submission()
                else:
                    await self.do_submission_remote()
            elif self.type == 1:
                await self.do_pretest()
            else:
                raise Exception('Unsupported type: {}'.format(self.type))
        except CompileError:
            self.end(status=STATUS_COMPILE_ERROR, score=0, time_ms=0, memory_kb=0)
        except ClientError:
            raise
        except Exception as e:
            logger.exception(e)
            self.next(judge_text=repr(e))
            self.end(status=STATUS_SYSTEM_ERROR, score=0, time_ms=0, memory_kb=0, judge_text=repr(e))

    async def update_problem_data(self):
        domain_id = self.request.pop('domain_id')
        pid = str(self.request.pop('pid'))
        await cache_invalidate(domain_id, pid)
        logger.debug('Invalidated %s/%s', domain_id, pid)
        await update_problem_data(self.session)

    async def do_submission(self):
        loop = get_event_loop()
        logger.info('Submission: %s, %s, %s', self.domain_id, self.pid, self.rid)
        cases_file_task = loop.create_task(cache_open(self.session, self.domain_id, self.pid))
        package = await self.build()
        with await cases_file_task as cases_file:
            await self.judge(cases_file, package)

    async def do_submission_remote(self):
        loop = get_event_loop()
        logger.info('Submission Remote: %s, %s, %s ( %s, %s )', self.domain_id, self.pid, self.rid,self.remote['orig_oj'],self.remote['orig_id'])
        #cases_file_task = loop.create_task(cache_open(self.session, self.domain_id, self.pid))
        #package = await self.build()
        #with await cases_file_task as cases_file:
        await self.judge_remote()

    async def do_pretest(self):
        loop = get_event_loop()
        logger.info('Pretest: %s, %s, %s', self.domain_id, self.pid, self.rid)
        cases_data_task = loop.create_task(self.session.record_pretest_data(self.rid))
        package = await self.build()
        with BytesIO(await cases_data_task) as cases_file:
            await self.judge(cases_file, package)

    async def build(self):
        self.next(status=STATUS_COMPILING)
        package, message, _, _ = await shield(build(self.lang, self.code.encode()))
        self.next(compiler_text=message)
        if not package:
            logger.debug('Compile error: %s', message)
            raise CompileError(message)
        return package

    async def judge(self, cases_file, package):
        loop = get_event_loop()
        self.next(status=STATUS_JUDGING, progress=0)
        cases = list(read_cases(cases_file))
        total_status = STATUS_ACCEPTED
        total_score = 0
        total_time_usage_ns = 0
        total_memory_usage_bytes = 0
        judge_tasks = list()
        for case in cases:
            judge_tasks.append(loop.create_task(case.judge(package)))
        for index, judge_task in enumerate(judge_tasks):
            status, score, time_usage_ns, memory_usage_bytes, stderr = await shield(judge_task)
            if self.type == 1:
                judge_text = stderr.decode(encoding='utf-8', errors='replace')
            else:
                judge_text = ''
            self.next(status=STATUS_JUDGING,
                      case={'status': status,
                            'score': score,
                            'time_ms': time_usage_ns // 1000000,
                            'memory_kb': memory_usage_bytes // 1024,
                            'judge_text': judge_text},
                      progress=(index + 1) * 100 // len(cases))
            total_status = max(total_status, status)
            total_score += score
            total_time_usage_ns += time_usage_ns
            total_memory_usage_bytes = max(total_memory_usage_bytes, memory_usage_bytes)
        self.end(status=total_status,
                 score=total_score,
                 time_ms=total_time_usage_ns // 1000000,
                 memory_kb=total_memory_usage_bytes // 1024)
                 
    async def judge_remote(self):
        loop = get_event_loop()
        self.next(status=STATUS_COMPILING, progress=0)
        if(self.remote['orig_oj']=="YBT"):
            logger.info('Choose %s Crawer To Remote: %s, %s', self.remote['orig_oj'], self.domain_id, ybt.username[ybt.now])
            while ybt.CheckSession()==False:
                logger.info('%s Crawer Is Logining', self.remote['orig_oj'])
                ybt.Login()
                time.sleep(1)
            recode_id = ybt.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Too Much Time')
            elif recode_id == '-2':
                raise Exception('Something Unexpected Happen')
            elif recode_id == '-3':
                raise Exception('Your program has restricted functions.')
            else:
                ybt.Monitor(recode_id,self.next,self.end)
            ybt.changeAccount()
        elif(self.remote['orig_oj']=="BZOI"):
            logger.info('Choose %s Crawer To Remote: %s, %s, %s', self.remote['orig_oj'], self.domain_id, self.pid, self.rid)
            while bzoj.CheckSession()==False:
                logger.info('%s Crawer Is Logining', self.remote['orig_oj'])
                bzoj.Login()
                time.sleep(1)
            recode_id = bzoj.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Too Much Time')
            elif recode_id == '-2':
                raise Exception('Something Unexpected Happen')
            else:
                bzoj.Monitor(recode_id,self.next,self.end)
            bzoj.changeAccount()
        elif(self.remote['orig_oj']=="XJOI"):
            logger.info('Choose %s Crawer To Remote: %s, %s, %s', self.remote['orig_oj'], self.domain_id, self.pid, self.rid)
            while xjoi.CheckSession()==False:
                logger.info('%s Crawer Is Logining', self.remote['orig_oj'])
                xjoi.Login()
                time.sleep(1)
            recode_id = xjoi.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Too Much Time')
            elif recode_id == '-2':
                raise Exception('Something Unexpected Happen')
            elif recode_id == '-3':
                raise Exception('Access Denied')
            else:
                xjoi.Monitor(recode_id,self.next,self.end)
            xjoi.changeAccount()
        elif(self.remote['orig_oj']=="CF"):
            if not self.lang in cf.SLanguage:
                raise Exception('LANGUAGE NOT SUPPORT')
            logger.info('Choose %s Crawer To Remote: %s, %s, %s', self.remote['orig_oj'], self.domain_id, self.pid, self.rid)
            recode_id = cf.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Failed')
            else:
                cf.Monitor(recode_id,self.next,self.end)
        elif(self.remote['orig_oj']=="POJ"):
            if not self.lang in poj.SLanguage:
                raise Exception('LANGUAGE NOT SUPPORT')
            logger.info('Choose %s Crawer To Remote: %s, %s, %s', self.remote['orig_oj'], self.domain_id, self.pid, self.rid)
            recode_id = poj.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Failed')
            else:
                poj.Monitor(recode_id,self.next,self.end)
        elif(self.remote['orig_oj']=="HDU"):
            if not self.lang in hdu.SLanguage:
                raise Exception('LANGUAGE NOT SUPPORT')
            logger.info('Choose %s Crawer To Remote: %s, %s, %s', self.remote['orig_oj'], self.domain_id, self.pid, self.rid)
            recode_id = hdu.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Failed')
            else:
                hdu.Monitor(recode_id,self.next,self.end)
        elif(self.remote['orig_oj']=="TK"):
            logger.info('Choose %s Crawer To Remote: %s, %s, %s', self.remote['orig_oj'], self.domain_id, self.pid, self.rid)
            while tk.CheckSession()==False:
                logger.info('%s Crawer Is Logining', self.remote['orig_oj'])
                tk.Login()
                time.sleep(1)
            recode_id = tk.Submit(self.remote['orig_id'],self.code,self.lang)
            if recode_id == '-1':
                raise Exception('Submit Too Much Time')
            elif recode_id == '-2':
                raise Exception('Something Unexpected Happen')
            elif recode_id == '-3':
                raise Exception('Auto-Verification Code Wrong! Please submit it again.')
            else:
                tk.Monitor(recode_id,self.next,self.end)
            tk.changeAccount()
        else:
            raise Exception('Do Not Support % judge',self.remote['orig_oj'])

    def next(self, **kwargs):
        self.ws.send_json({'key': 'next', 'tag': self.tag, **kwargs})

    def end(self, **kwargs):
        self.ws.send_json({'key': 'end', 'tag': self.tag, **kwargs})

#ybt_sys = YBTJudge(config['YBT_uname'],config['YBT_pwd'],True)
ybt_sys = YBTJudge(config['YBT_uname'],config['YBT_cookies'],True,True)
bzoj_sys = DBzojJudge(config['BZOJ_uname'],config['BZOJ_pwd'],True)
xjoi_sys = XJOIJudge(config['XJOI_uname'],config['XJOI_pwd'],True)
cf_sys = CFJudge()
poj_sys = POJJudge()
hdu_sys = HDUJudge()
tk_sys = TKJudge(config['TK_uname'],config['TK_pwd'],True)

ybt = ybt_sys
bzoj = bzoj_sys
xjoi = xjoi_sys
cf = cf_sys
poj = poj_sys
hdu = hdu_sys
tk = tk_sys

async def update_problem_data(session):
    logger.info('Update problem data')
    result = await session.judge_datalist(config.get('last_update_at', 0))
    for pid in result['pids']:
        await cache_invalidate(pid['domain_id'], str(pid['pid']))
        logger.debug('Invalidated %s/%s', pid['domain_id'], str(pid['pid']))
    config['last_update_at'] = result['time']
    await save_config()

async def do_judge(session):
    await update_problem_data(session)
    await session.judge_consume(JudgeHandler)

async def do_noop(session):
    while True:
        await sleep(3600)
        logger.info('Updating session')
        await session.judge_noop()

async def daemon():
    try_init_cgroup()
    
    async with VJ4Session(config['server_url']) as session:
        while True:
            try:
                await session.login_if_needed(config['uname'], config['password'])
                done, pending = await wait([do_judge(session), do_noop(session)],
                                           return_when=FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await gather(*done)
            except Exception as e:
                logger.exception(e)
            logger.info('Retrying after %d seconds', RETRY_DELAY_SEC)
            await sleep(RETRY_DELAY_SEC)

if __name__ == '__main__':
    get_event_loop().run_until_complete(daemon())
