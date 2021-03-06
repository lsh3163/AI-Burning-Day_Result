# -*- coding: utf-8 -*-
"""pose_estimation.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1s5TCdoR2uOhXcbsJv0MFvvZX4_V2BqHp
"""

def get_image_list(image_path):
  with os.scandir(image_path) as entries:
    image_list = [entry.name for entry in entries if os.path.isfile(image_path+"/"+entry.name) and entry.name.endswith('.png')]
  return sorted(image_list)

def get_pose_list(image_list, image_path, headers, url):
  pose_list = list()
  while None in pose_list or len(pose_list) == 0:
    for image in tqdm(image_list):
      files = {
        'image': open(image_path+'/'+image, 'rb')
      }
      response = requests.post(url, files=files, headers=headers)
      rescode = response.status_code
      if(rescode == 200):
        pose_list.append(json.loads(response.text))
      else:
        pose_list.append(None)
  return pose_list

client_id = "naver client id"
client_secret = "naver client secret"
url = "https://naveropenapi.apigw.ntruss.com/vision-pose/v1/estimate"
headers = {
    'X-NCP-APIGW-API-KEY-ID': client_id,
    'X-NCP-APIGW-API-KEY': client_secret
}

project_path = "./"
ori_image_path = project_path + 'crawling/'
pre_ori_images_list = get_image_list(ori_image_path)

# pose estimation
pre_pose_list = get_pose_list(pre_ori_images_list, ori_image_path, headers, url)