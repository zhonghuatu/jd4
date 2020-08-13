# encoding=utf8
import pytesseract,os
from PIL import Image
 
def sum_9_region_new(img, x, y):
    '''确定噪点 '''
    cur_pixel = img.getpixel((x, y))  # 当前像素点的值
    width = img.width
    height = img.height
 
    if cur_pixel == 1:  # 如果当前点为白色区域,则不统计邻域值
        return 0
 
    # 因当前图片的四周都有黑点，所以周围的黑点可以去除
    if y < 3:  # 本例中，前两行的黑点都可以去除
        return 1
    elif y > height - 3:  # 最下面两行
        return 1
    else:  # y不在边界
        if x < 3:  # 前两列
            return 1
        elif x == width - 1:  # 右边非顶点
            return 1
        else:  # 具备9领域条件的
            sum = img.getpixel((x - 1, y - 1)) \
                  + img.getpixel((x - 1, y)) \
                  + img.getpixel((x - 1, y + 1)) \
                  + img.getpixel((x, y - 1)) \
                  + cur_pixel \
                  + img.getpixel((x, y + 1)) \
                  + img.getpixel((x + 1, y - 1)) \
                  + img.getpixel((x + 1, y)) \
                  + img.getpixel((x + 1, y + 1))
            return 9 - sum
 
def collect_noise_point(img):
    '''收集所有的噪点'''
    noise_point_list = []
    for x in range(img.width):
        for y in range(img.height):
            res_9 = sum_9_region_new(img, x, y)
            if (0 < res_9 < 3) and img.getpixel((x, y)) == 0:  # 找到孤立点
                pos = (x, y)
                noise_point_list.append(pos)
    return noise_point_list
 
def remove_noise_pixel(img, noise_point_list):
    '''根据噪点的位置信息，消除二值图片的黑点噪声'''
    for item in noise_point_list:
        img.putpixel((item[0], item[1]), 1)
 
def get_bin_table(threshold=120):
    '''获取灰度转二值的映射table,0表示黑色,1表示白色'''
    table = []
    for i in range(256):
        if i < threshold:
            table.append(0)
        else:
            table.append(1)
    return table
 
def main():
    image = Image.open('vcode.gif')
    imgry = image.convert('L')
    '''for i in range(100,150,5):
        table = get_bin_table(i)
        binary = imgry.point(table, '1')
        noise_point_list = collect_noise_point(binary)
        remove_noise_pixel(binary, noise_point_list)
        binary.save('try/{}.gif'.format(i))\''''
    table = get_bin_table()
    binary = imgry.point(table, '1')
    noise_point_list = collect_noise_point(binary)
    remove_noise_pixel(binary, noise_point_list)
    binary = binary.convert('RGB')
    binary.save('try.jpg')
    # 识别
    text = pytesseract.image_to_string(binary, lang='eng', \
        config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
    #print("识别结果："+text)
    #
    return text
 
def recog(img):
    image = Image.open(img)
    imgry = image.convert('L')
    table = get_bin_table()
    binary = imgry.point(table, '1')
    noise_point_list = collect_noise_point(binary)
    remove_noise_pixel(binary, noise_point_list)
    binary = binary.convert('RGB')
    # 识别
    text = pytesseract.image_to_string(binary, lang='eng', \
        config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
    return text
 
if __name__ == '__main__':
    main()