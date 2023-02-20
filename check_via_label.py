import os
import xml.etree.ElementTree as ET
from PIL import Image
import csv
import cv2
import shutil
from unicodedata import normalize
import re


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
# bbox 좌상우하순으로 정렬
# 숫자,글자 순으로 밖에 정렬 안됨
# 한번돌리면 인코딩에러뜸...
##################################################################
def sort_bounding_boxes(xml_dir):
    xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
    for xml_file in xml_files:
        xml_path = os.path.join(xml_dir, xml_file)
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find all bounding box elements
        bboxes = []
        for obj in root.iter("object"):
            bndbox = obj.find("bndbox")
            xmin = int(bndbox.find("xmin").text)
            ymin = int(bndbox.find("ymin").text)
            xmax = int(bndbox.find("xmax").text)
            ymax = int(bndbox.find("ymax").text)
            bboxes.append((xmin, ymin, xmax, ymax))

        # Sort the bounding boxes based on top-left coordinate (xmin, ymin)
        bboxes.sort(key=lambda x: (x[0], x[1]))

        # Update the XML file with the sorted bounding boxes
        for i, obj in enumerate(root.iter("object")):
            bndbox = obj.find("bndbox")
            bndbox.find("xmin").text = str(bboxes[i][0])
            bndbox.find("ymin").text = str(bboxes[i][1])
            bndbox.find("xmax").text = str(bboxes[i][2])
            bndbox.find("ymax").text = str(bboxes[i][3])

        tree.write(xml_path, encoding='utf8')


##################################################################
# bbox 좌상우하순으로 name이랑 같이 정렬
##################################################################

def sort_nameBybboxes(input_folder_path, output_folder_path):
    # Create the output folder if it does not exist
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    # Process each XML file in the input folder
    for filename in os.listdir(input_folder_path):
        if not filename.endswith('.xml'):
            continue

        # Parse the XML file
        input_file_path = os.path.join(input_folder_path, filename)
        output_file_path = os.path.join(output_folder_path, filename)
        tree = ET.parse(input_file_path)
        root = tree.getroot()

        # Extract the bounding boxes and names
        bboxes = []
        names = []
        for obj in root.findall('object'):
            bbox = obj.find('bndbox')
            xmin = int(bbox.find('xmin').text)
            ymin = int(bbox.find('ymin').text)
            xmax = int(bbox.find('xmax').text)
            ymax = int(bbox.find('ymax').text)
            bboxes.append((xmin, ymin, xmax, ymax))
            names.append(obj.find('name').text)

        # Sort the bounding boxes and names
        sorted_bboxes = sorted(bboxes, key=lambda bbox: (bbox[0], bbox[1]))
        sorted_names = [name for _, name in sorted(zip(bboxes, names), key=lambda pair: pair[0])]

        # Update the XML file with the sorted bounding boxes and names
        for i, obj in enumerate(root.findall('object')):
            bbox = obj.find('bndbox')
            bbox.find('xmin').text = str(sorted_bboxes[i][0])
            bbox.find('ymin').text = str(sorted_bboxes[i][1])
            bbox.find('xmax').text = str(sorted_bboxes[i][2])
            bbox.find('ymax').text = str(sorted_bboxes[i][3])
            obj.find('name').text = sorted_names[i]

        # Write the updated XML file
        tree.write(output_file_path, encoding='utf-8')

    return



##################################################################
# 좌상우하순으로 정렬된 bbox로 짝 xml, img 파일명 모두 바꾸기
# N_, S_, A3_ 삭제 필요
# Example usage: rename_xml_image_files('/path/to/xml/files')
##################################################################


def rename_xml_image_files(xml_folder, images_folder, renamed_folder):
    os.makedirs(renamed_folder, exist_ok=True)
    xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]
    for xml_file in xml_files:
        xml_path = os.path.join(xml_folder, xml_file)
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # extract the object name from the XML file
        names = []
        for obj in root.findall('object'):
            name = obj.find("name").text
            if name != 'Plate':
                names.append(obj.find('name').text)


            new_filename = renamed_folder + "/" + "-".join(names) + "_sorted.xml"
            new_xml = normalize('NFC', new_filename) #한글깨짐방지

            old_xml_file_path = os.path.join(xml_folder, xml_file)
            old_xml = normalize('NFC',old_xml_file_path) #한글깨짐방지

            os.rename(old_xml, new_xml)

        image_file_path = os.path.join(images_folder, xml_file[:-4] + '.jpg')
        if os.path.exists(image_file_path):
            old_image_file_path = image_file_path
            old_image = normalize('NFC', old_image_file_path) #한글깨짐방지
            new_image_file_path = os.path.join(images_folder, xml_file[:-4] + '_sorted.jpg')
            os.rename(old_image, new_image_file_path)



if __name__ == '__main__':
    # check_and_move_unpaired('E:/LPR_7차학습/Class_C2/Class_C2_3/images/src', 'E:/LPR_7차학습/Class_C2/Class_C2_3/labels/src', 'E:/LPR_7차학습/Class_C2/Class_C2_3/unpaired')
    # check_and_fix_xml_sizes('E:/LPR_7차학습/Class_C2/Class_C2_3/images/src', 'E:/LPR_7차학습/Class_C2/Class_C2_3/labels/src')
    #crop_objects(images_folder='E:/PycharmProjects/yolo_data_util_enshin/Data/test/images', xml_folder='E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels', cropped_folder='E:/PycharmProjects/yolo_data_util_enshin/Data/test/cropped')
    #sort_bounding_boxes('E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels')
    #sort_nameBybboxes('E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels')
    rename_xml_image_files('E:/PycharmProjects/yolo_data_util_enshin/Data/test/labels','E:/PycharmProjects/yolo_data_util_enshin/Data/test/images', 'E:/PycharmProjects/yolo_data_util_enshin/Data/test/renamed')



















