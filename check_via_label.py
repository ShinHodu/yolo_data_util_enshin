import os
import xml.etree.ElementTree as ET
from PIL import Image
import csv
import cv2
import shutil
from unicodedata import normalize
import random
import re
from distutils.dir_util import copy_tree

##################################################################
# random 으로 짝 img, xml 뽑기
##################################################################

def extract_image_xml_pairs(img_dir, xml_dir, num_pairs, output_img_dir, output_xml_dir):
    # Get the list of filenames in the img folder
    img_filenames = list(set(os.listdir(img_dir)) - {'desktop.ini', 'whatever.ini'})

    # Shuffle the list of filenames randomly
    random.shuffle(img_filenames)

    # Extract the specified number of image and XML file pairs
    pairs = []
    for i in range(num_pairs):
        # Choose the next image filename in the shuffled list
        random_img_filename = img_filenames[i]

        # Create the corresponding xml filename
        xml_filename = os.path.splitext(random_img_filename)[0] + ".xml"

        # Define the paths to the selected image and xml files
        selected_img_path = os.path.join(img_dir, random_img_filename)
        selected_xml_path = os.path.join(xml_dir, xml_filename)

        # Create the output folder if it does not exist
        if not os.path.exists(output_img_dir):
            os.makedirs(output_img_dir)
        if not os.path.exists(output_xml_dir):
            os.makedirs(output_xml_dir)
        # Define the paths to the output image and xml files
        output_img_path = os.path.join(output_img_dir, random_img_filename)
        output_xml_path = os.path.join(output_xml_dir, xml_filename)

        # Copy the selected image and xml files to the output directory
        shutil.copy(selected_img_path, output_img_path)
        shutil.copy(selected_xml_path, output_xml_path)

        # Add the selected image and xml file paths to the list of pairs
        pairs.append((output_img_path, output_xml_path))

    return pairs



##################################################################
# img, xml, unpaired 폴더
# 짝 확인 후 짝없는 데이터는 unpaired 폴더로 이동
# Example usage: check_and_move_unpaired('/path/to/image/folder', '/path/to/xml/folder', '/path/to/unpaired/folder')
##################################################################
def check_and_move_unpaired(img_folder, xml_folder, unpaired_folder):
    os.makedirs(unpaired_folder, exist_ok=True)
    # list of image files
    img_files = [f for f in os.listdir(img_folder) if f.endswith('.jpg')]
    # list of xml files
    xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]

    # loop through image files
    for img_file in img_files:
        xml_file = img_file.replace('.jpg', '.xml')
        if xml_file in xml_files:
            continue
        else:
            print(f"!! {img_file}-> 짝 xml 없음 !!")
            src_path = os.path.join(img_folder, img_file)
            dst_path = os.path.join(unpaired_folder, img_file)
            shutil.move(src_path, dst_path)

    # loop through xml files
    for xml_file in xml_files:
        img_file = xml_file.replace('.xml', '.jpg')
        if img_file in img_files:
            continue
        else:
            print(f"!! {xml_file}-> 짝 이미지 없음 !!")
            src_path = os.path.join(xml_folder, xml_file)
            dst_path = os.path.join(unpaired_folder, xml_file)
            shutil.move(src_path, dst_path)

##################################################################
# img와 짝이 맞는 xml이 짝 img의 사이즈를 갖도록한다
# Example usage: check_and_fix_xml_sizes('/path/to/images', '/path/to/xmls')
##################################################################
def check_and_fix_xml_sizes(img_folder, xml_folder):
    # list all the files in both folders
    img_files = [f for f in os.listdir(img_folder) if f.endswith('.jpg')]
    xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]

    # check if every image has its paired xml
    for img in img_files:
        xml_name = img.replace('.jpg', '.xml')
        if xml_name not in xml_files:
            print(f"!! {img} -> 짝 xml 없음 !!")

    # check if xml has the right image size, fix it if not
    for xml_file in xml_files:
        xml_path = os.path.join(xml_folder, xml_file)
        tree = ET.parse(xml_path)
        root = tree.getroot()
        size = root.find('size')
        width = int(size.find('width').text)
        height = int(size.find('height').text)

        img_name = xml_file.replace('.xml', '.jpg')
        img_path = os.path.join(img_folder, img_name)
        if not os.path.exists(img_path):
            print(f"!! {xml_file} -> 짝 이미지 없음 !!")
        else:
            img_width, img_height = Image.open(img_path).size
            if img_width != width or img_height != height:
                print(f"{xml_file} Size 교정중...")
                size.find('width').text = str(img_width)
                size.find('height').text = str(img_height)
                tree.write(xml_path, encoding='utf8')


##################################################################
# xml에서 인수로 입력받은 name기준 수량 체크 후 csv로 카운트파일 저장
# Example usage: count_objects_per_name('/path/to/xmls', 'obj name', '/path/to/csv file')
##################################################################
def count_objects_per_name(folder_path, tag_name, csv_file):
    object_counts = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".xml"):
            file_path = os.path.join(folder_path, filename)
            tree = ET.parse(file_path)
            root = tree.getroot()
            for elem in root.iter(tag_name):
                object_name = elem.attrib.get("name")
                if object_name in object_counts:
                    object_counts[object_name] += 1
                else:
                    object_counts[object_name] = 1

    with open(csv_file, 'w', newline='', encoding='utf8') as f:
        writer = csv.writer(f, encoding='utf8')
        writer.writerow(["Name", "Count"])
        for key, value in object_counts.items():
            writer.writerow([key, value])


##################################################################
# xml의 object의 name별로 img crop하고 각 name에 해당는 폴더에 넣기
# cropped image에 해당하는 xml파일 생성X
# Example usage:
#               images_folder = "path/to/images"
#               xml_folder = "path/to/xml"
#               crop_objects(images_folder, xml_folder)
##################################################################
def crop_objects(images_folder, xml_folder, cropped_folder):
    for filename in os.listdir(images_folder):
        # check if file is an image
        if filename.endswith(".jpg") or filename.endswith(".png"):
            # read the image file
            img = cv2.imread(os.path.join(images_folder, filename))
            # get the corresponding XML file
            xml_file = os.path.splitext(filename)[0] + ".xml"
            xml_path = os.path.join(xml_folder, xml_file)
            cropped_xml_path = os.path.join(cropped_folder, xml_file)
            # read the XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()
            # iterate through the objects in the XML file
            for obj in root.iter("object"):
                class_name = obj.find("name").text
                # create a folder for each object class
                class_folder = os.path.join(cropped_folder, class_name)
                if not os.path.exists(class_folder):
                    os.makedirs(class_folder)
                bndbox = obj.find("bndbox")
                xmin = int(bndbox.find("xmin").text)
                ymin = int(bndbox.find("ymin").text)
                xmax = int(bndbox.find("xmax").text)
                ymax = int(bndbox.find("ymax").text)

                # crop the object from the image
                cropped_obj = img[ymin:ymax, xmin:xmax]
                # save the cropped object in the corresponding class folder
                cropped_obj_path = os.path.join(class_folder, filename)
                cv2.imwrite(cropped_obj_path, cropped_obj)
                #tree.write(cropped_xml_path, encoding='utf8')



##################################################################
# bbox 좌상우하순으로 name이랑 같이 정렬
# !!! A_ 있으면 앞으로 빼기
##################################################################
def sort_nameBybboxes(input_folder_path, output_folder_path):
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    xml_files = [os.path.join(input_folder_path, f) for f in os.listdir(input_folder_path) if f.endswith('.xml')]

    for xml_file in xml_files:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        bboxes = []
        names = []
        for obj in root.findall('object'):
            bbox_elem = obj.find('bndbox')
            bbox = (
                int(bbox_elem.find('xmin').text),
                int(bbox_elem.find('ymin').text),
                int(bbox_elem.find('xmax').text),
                int(bbox_elem.find('ymax').text)
            )
            name = obj.find('name').text
            bboxes.append(bbox)
            names.append(name)

        bbox_names = [(bbox, name, 1 if not name.startswith("A") else 0) for bbox, name in zip(bboxes, names)]
        #bbox_names.sort(key=lambda x: (x[2], x[0], x[1], x[3]))
        bbox_names.sort(key=lambda x: (x[2], x[0], x[1]))

        sorted_bboxes = [bbox_name[0] for bbox_name in bbox_names]
        sorted_names = [bbox_name[1] for bbox_name in bbox_names]

        i = 0
        for obj in root.findall('object'):
            bbox_elem = obj.find('bndbox')
            bbox_elem.find('xmin').text = str(sorted_bboxes[i][0])
            bbox_elem.find('ymin').text = str(sorted_bboxes[i][1])
            bbox_elem.find('xmax').text = str(sorted_bboxes[i][2])
            bbox_elem.find('ymax').text = str(sorted_bboxes[i][3])
            obj.find('name').text = sorted_names[i]
            i += 1

        output_xml_file = os.path.join(output_folder_path, os.path.basename(xml_file))
        tree.write(output_xml_file, encoding='utf8')


##################################################################
# xml 속 name순으로 짝 xml, img 파일명 모두 바꾸기
# 변경된 파일명이 중복이면 뒤에 숫자 붙이기
# Example usage: rename_xml_image_files('/path/to/xml/files')
##################################################################

def rename_xml_image_files(xml_folder, images_folder, renamed_xml_folder, renamed_img_folder):
    copy_tree(xml_folder, renamed_xml_folder)
    copy_tree(images_folder, renamed_img_folder)

    xml_files = [f for f in os.listdir(renamed_xml_folder) if f.endswith('.xml')]
    for xml_file in xml_files:
        xml_path = os.path.join(xml_folder, xml_file)
        tree = ET.parse(xml_path)
        root = tree.getroot()
        object_names = []
        for obj in root.findall('object'):
            name = obj.find('name').text
            if name != "Plate": #Plate 제외
                object_names.append(name)

        old_xml_path = normalize('NFC', os.path.join(renamed_xml_folder, xml_file)) #한글깨짐방지
        new_xml_name = normalize('NFC',"".join(object_names) + ".xml") #한글깨짐방지

        # 중복 파일명 처리: 끝에 숫자 붙이기
        if os.path.exists(os.path.join(renamed_xml_folder, new_xml_name)):
            i = 1
            while True:
                numbered_xml_name = f"{new_xml_name[:-4]}_{i}.xml"
                if not os.path.exists(os.path.join(renamed_xml_folder, numbered_xml_name)):
                    new_xml_name = numbered_xml_name
                    break
                i += 1

        os.rename(os.path.join(renamed_xml_folder, xml_file), os.path.join(renamed_xml_folder, new_xml_name))

        img_files = [f for f in os.listdir(renamed_img_folder) if f.endswith('.jpg')]
        old_img_path = normalize('NFC', os.path.join(renamed_img_folder, xml_file[:-4] + '.jpg'))
        for img_file in img_files:
            if old_img_path == os.path.join(renamed_img_folder, img_file[:-4] + '.jpg'):
                new_img_file_path = os.path.join(renamed_img_folder, new_xml_name[:-4] + '.jpg')
                os.rename(old_img_path, new_img_file_path)

##################################################################
# 이지네이머가 더 편리함,,!
# Remove Target char 'A1~3_,S_,N_' from file name
# extension: ".jpg" or ".xml"
##################################################################
def filename_remove_targetchar(folder_path,extension):
    for filename in os.listdir(folder_path):
        if filename.endswith(extension):
            new_filename = re.sub('A3_|S_|N_', '',filename)
            os.rename(os.path.join(folder_path, filename), os.path.join(folder_path, new_filename))



##################################################################
# 폴더 속 이미지 평균 가로/세로 구하기
# avg_width, avg_height = get_average_size('이미지 경로')
# print(f"Average width: {avg_width}")
# print(f"Average height: {avg_height}")
##################################################################
def get_average_img_size(img_folder_path):
    total_width = 0
    total_height = 0
    num_images = 0

    for filename in os.listdir(img_folder_path):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            img_path = os.path.join(img_folder_path, filename)

            img = Image.open(img_path)
            width, height = img.size
            total_width += width
            total_height += height
            num_images += 1
            print(img_path, width, height)

    avg_width = total_width / num_images
    avg_height = total_height / num_images

    print(f"Average width: {avg_width}")
    print(f"Average height: {avg_height}")
    #return avg_width, avg_height


##################################################################
# Plate 평균 가로/세로 구하기
# avg_width, avg_height = get_average_Plate_size('이미지 경로','xml 경로')
# print(f"Average width: {avg_width}")
# print(f"Average height: {avg_height}")
##################################################################

def get_average_Plate_size(xml_folder_path):
    total_width = 0
    total_height = 0
    plate_count = 0

    for filename in os.listdir(xml_folder_path):
        if filename.endswith('.xml'):
            xml_path = os.path.join(xml_folder_path, filename.split('.')[0] + '.xml')

            if os.path.exists(xml_path):
                tree = ET.parse(xml_path)
                root = tree.getroot()

                for obj in root.findall('object'):
                    name = obj.find('name').text
                    if name == 'Plate':
                        bbox = obj.find('bndbox')
                        xmin = int(bbox.find('xmin').text)
                        ymin = int(bbox.find('ymin').text)
                        xmax = int(bbox.find('xmax').text)
                        ymax = int(bbox.find('ymax').text)
                        width = xmax - xmin
                        height = ymax - ymin
                        total_width += width
                        total_height += height
                        plate_count += 1
                        print(xml_path, width, height)

    if plate_count > 0:
        avg_width = total_width / plate_count
        avg_height = total_height / plate_count

        print(f"Average width: {avg_width}")
        print(f"Average height: {avg_height}")




if __name__ == '__main__':
    #extract_image_xml_pairs('E:/PycharmProjects/yolo_data_util_enshin/Data/test/LPR_OCR/Class_E/images/전면', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/LPR_OCR/Class_E/labels/전면', 2000, 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/LPR_OCR/random2000/Class_E/images/src', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/LPR_OCR/random2000/Class_E/labels/src')

    #check_and_move_unpaired('E:/PycharmProjects/yolo_data_util_enshin/Data/test/LPR_OCR/Class_E/images/전면', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/LPR_OCR/Class_E/labels/전면', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/unpaired')

    #check_and_fix_xml_sizes('E:/PycharmProjects/yolo_data_util_enshin/Data/test/images', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels')

    #crop_objects(images_folder='E:/PycharmProjects/yolo_data_util_enshin/Data/test/images', xml_folder='E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels', cropped_folder='E:/PycharmProjects/yolo_data_util_enshin/Data/test/cropped')

    #sort_nameBybboxes('E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/renamed/labels')

    #rename_xml_image_files('E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels','E:/PycharmProjects/yolo_data_util_enshin/Data/test/images', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/renamed/labels', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/renamed/images')

    #get_average_img_size('E:/RT_Projects/Data/LPR_Region_1/Class_Z/images/src')
    get_average_Plate_size('E:/RT_Projects/Data/LPR_Region_1/Class_Z/labels/src')





















