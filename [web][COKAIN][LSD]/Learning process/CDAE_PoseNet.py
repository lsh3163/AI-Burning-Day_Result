# -*- coding: utf-8 -*-
"""CDAE_POSENET.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10uMA9ua7tt-RDmOmtudXWTS293oivoAq
"""

# Commented out IPython magic to ensure Python compatibility.
from __future__ import absolute_import, division, print_function, unicode_literals
try:
  # %tensorflow_version only exists in Colab.
#   %tensorflow_version 2.x
except Exception:
  pass
import tensorflow as tf

import os
import requests
import time
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import json
import pickle
import copy
import cv2
from google.colab.patches import cv2_imshow

from tqdm.auto import tqdm

from IPython import display

def get_image_list(image_path):
  with os.scandir(image_path) as entries:
    image_list = [entry.name for entry in entries if os.path.isfile(image_path+"/"+entry.name) and entry.name.endswith('.png')]
  return sorted(image_list)

def filter_image_pose(pre_ori_images_list, pre_edge_images_list, pre_pose_list):
  ori_images_list = list()
  edge_images_list = list()
  pose_list = list()

  for i, pose_value in enumerate(pre_pose_list):
    if len(pose_value['predictions']) > 1:
      poses = pose_value['predictions']
      avg_score = list()
      for pose in poses:
        pose_score_sum = 0
        key_num = 0
        for key in pose.keys():
          pose_score_sum += pose[key]['score']
          key_num +=1
        avg_score.append(pose_score_sum/key_num)
      pose_idx = avg_score.index(max(avg_score))
      pose_value['predictions'] = [poses[pose_idx]]

      ori_images_list.append(pre_ori_images_list[i])
      edge_images_list.append(pre_edge_images_list[i])
      pose_list.append(pre_pose_list[i])
    elif len(pose_value['predictions']) == 0:
      continue
    else:
      ori_images_list.append(pre_ori_images_list[i])
      edge_images_list.append(pre_edge_images_list[i])
      pose_list.append(pre_pose_list[i])
  return ori_images_list, edge_images_list, pose_list


def pose_list_to_vector(pose_list):
  # pose_list to vector information
  pose_vectors = list()
  for pose_value in pose_list:
    pose = pose_value['predictions'][0]
    pose_loci = list()
    for i in range(18):
      if str(i) in pose.keys():
        pose_loci.append(1)
        pose_loci.append(pose[str(i)]['x'])
        pose_loci.append(pose[str(i)]['y'])
      else:
        pose_loci.append(0)
        pose_loci.append(0)
        pose_loci.append(0)
    pose_vectors.append(pose_loci)
  pose_vectors = np.asarray(pose_vectors).astype('float32')
  return pose_vectors

def convert_image_to_numpy(edge_images_list, edge_image_path):
  train_edge_images = list()
  for edge_image in tqdm(edge_images_list):
    im = np.array(Image.open(edge_image_path + '/' + edge_image))
    train_edge_images.append(im)
  train_edge_images = np.asarray(train_edge_images)
  return train_edge_images


def predict_pose(dae, posenet, edge_image_path, edge_images_list, pose_num):
  edge_im_input = np.array(Image.open(edge_image_path + '/' + edge_images_list[pose_num])).reshape(256, 256, 1).astype('float32')
  edge_im_input = edge_im_input /255
  tf.convert_to_tensor([edge_im_input])
  pred_pose = posenet.predict(cae.encode(predictions))
  return pred_pose

def generate_and_save_images(model, epoch, test_input, test_noisy_images ,test_images):
  predictions = model.predict(test_input)
  fig = plt.figure(figsize=(11,11))

  for i in range(predictions.shape[0]):
      plt.subplot(12, 4, i+1)
      plt.imshow(predictions[i, :, :, 0], cmap='gray')
      plt.axis('off')

  for i in range(test_noisy_images.shape[0]):
      plt.subplot(12, 4, i+1+16)
      plt.imshow(test_noisy_images[i, :, :, 0], cmap='gray')
      plt.axis('off')
    
  for i in range(test_images.shape[0]):
      plt.subplot(12, 4, i+1+32)
      plt.imshow(test_images[i, :, :, 0], cmap='gray')
      plt.axis('off')

  # tight_layout minimizes the overlap between 2 sub-plots
  plt.tight_layout()
  plt.show()

def prepare_dataset(ori_image_path, edge_image_path, load_edge_numpy = True):
  pre_ori_images_list = get_image_list(ori_image_path)
  pre_edge_images_list = get_image_list(edge_image_path)

  pre_image_pose_list = pickle.load(open(ori_image_path+"pose_list.p", "rb"))
  pre_pose_list = pre_image_pose_list[1]

  # Filter images without pose estimation
  ori_images_list, edge_images_list, pose_list = filter_image_pose(pre_ori_images_list, pre_edge_images_list, pre_pose_list)

  # Convert edge_images to numpy array
  if load_edge_numpy:
    train_edge_images = pickle.load(open(ori_image_path+"pose_numpy.p", "rb"))
  else:
    train_edge_images = convert_image_to_numpy(edge_images_list, edge_image_path)
    pickle.dump(train_edge_images, open(ori_image_path+"pose_numpy.p", "wb"))
  

  # pose_list to vector information
  pose_labels = pose_list_to_vector(pose_list)

  # Data preprocessing, normalization
  train_edge_images = train_edge_images.reshape(train_edge_images.shape[0], 256, 256, 1).astype('float32')
  train_edge_images /= 255.

  # Shuffle data
  train_idx = np.arange(len(train_edge_images))
  np.random.shuffle(train_idx)

  train_edge_images = np.array([train_edge_images[idx] for idx in train_idx])
  pose_labels = np.array([pose_labels[idx] for idx in train_idx])

  # Noise to train data
  noise_factor = 0.5
  train_noisy = train_edge_images + noise_factor*tf.random.normal(shape=train_edge_images.shape)

  train_noisy = tf.clip_by_value(train_noisy, clip_value_min=0., clip_value_max=1.)

  # Data to tensor data set
  train_dataset = tf.convert_to_tensor(train_edge_images)
  train_noisy_dataset = tf.convert_to_tensor(train_noisy)

  pose_dataset = tf.convert_to_tensor(pose_labels)

  return train_dataset, train_noisy_dataset, pose_dataset, train_noisy

def get_image_list_for_test(ori_image_path, edge_image_path):
  pre_ori_images_list = get_image_list(ori_image_path)
  pre_edge_images_list = get_image_list(edge_image_path)

  pre_image_pose_list = pickle.load(open(ori_image_path+"pose_list.p", "rb"))
  pre_pose_list = pre_image_pose_list[1]

  # Filter images without pose estimation
  ori_images_list, edge_images_list, pose_list = filter_image_pose(pre_ori_images_list, pre_edge_images_list, pre_pose_list)
  return ori_images_list, edge_images_list, pose_list

def show_png_image(image_path, image_name_list, image_num):
  im_array = np.array(Image.open(image_path+image_name_list[image_num]))
  plt.imshow(im_array)
  plt.axis('off')
  plt.show()

def show_result_image(cdae, input_dataset, input_original):
  prediction = cdae.predict(input_dataset)
  fig = plt.figure(figsize=(3,3))
  plt.subplot(3,1, 1)
  plt.imshow(prediction[0, :, :, 0], cmap='gray')
  plt.axis('off')
  plt.subplot(3,1, 2)
  plt.imshow(input_dataset[0, :, :, 0], cmap='gray')
  plt.axis('off')
  plt.subplot(3,1, 3)
  plt.imshow(input_original[0, :, :, 0], cmap='gray')
  plt.axis('off')
  plt.show()

def show_pose_label(cdae, posenet, ori_image_path, edge_image_path, ore_image_name_list, edge_image_name_list, label_list, image_num):
  ori_im = Image.open(ori_image_path+ore_image_name_list[image_num])
  edge_im = Image.open(edge_image_path+edge_image_name_list[image_num])
  edge_im_array = np.array(edge_im).reshape(256, 256, 1).astype('float32')
  edge_im_array = edge_im_array /255

  estimated_label = posenet.predict(cdae.encode(tf.convert_to_tensor([edge_im_array])))

  print(estimated_label.shape)
  ori_im.convert('RGB') 
  open_cv_image_ori = np.array(ori_im, dtype=np.float32) 
  open_cv_image_ori = open_cv_image_ori[:, :, ::-1].copy()

  test_labels = [value for i, value in enumerate(estimated_label[0]) if i % 3 == 0]
  for i in range(len(test_labels)):
    if test_labels[i] < 0.5:
      estimated_label[0][i*3+1] = 0
      estimated_label[0][i*3+2] = 0

  label_dict = label_list[image_num]['predictions'][0]
  ori_label = list()
  for i in range(18):
    if str(i) in label_dict.keys():
      ori_label.append(label_dict[str(i)]['x'])
      ori_label.append(label_dict[str(i)]['y'])
    else:
      ori_label.append(0)
      ori_label.append(0)

  font = cv2.FONT_HERSHEY_SIMPLEX
  for i in range(18):
    x = estimated_label[0][i*3+1]
    y = estimated_label[0][i*3+2]
    x_ori = ori_label[i*2]
    y_ori = ori_label[i*2+1]
    if x != 0:
      cv2.putText(open_cv_image_ori, str(i), (int(640*x)-5,int(640*y)), font, 0.5, (255,0,0), 2)
    if x_ori != 0:
      cv2.putText(open_cv_image_ori, str(i), (int(640*x_ori)-5,int(640*y_ori)), font, 0.5, (0,0,255), 1)
    # cv2.circle(open_cv_image, (int(640*x), int(640*y)), 10, (255,0,0), 2)
    # cv2.circle(open_cv_image, (int(640*x_ori), int(640*y_ori)), 10, (0,0,255), 1)
    
    
  cv2_imshow(open_cv_image_ori)

# # pose estimation
# pre_pose_list = get_pose_list(pre_ori_images_list, ori_image_path, headers, url)
# pickle.dump(pre_pose_list, open("/content/drive/My Drive/Colab Notebooks/Projects/COKAIN/crawling/pose_list.p", "wb"))

project_path = '/content/drive/My Drive/Colab Notebooks/Projects/COKAIN/'
# project_path = '../'

lsd_model_weight = project_path + "crawling/LSD_model_weights/"

train_ori_image_path = project_path + 'crawling/'
train_edge_image_path = train_ori_image_path + "edge/"

train_dataset, train_noisy_dataset, train_pose_dataset, train_noisy = prepare_dataset(train_ori_image_path, train_edge_image_path)

test_ori_image_path = project_path + '5cha/'
test_edge_image_path = test_ori_image_path + "edge/"

test_dataset, test_noisy_dataset, test_pose_dataset, test_noisy = prepare_dataset(test_ori_image_path, test_edge_image_path)

# Learning parameter setup
epochs = 100
BATCH_SIZE = 64
latent_dim = 256
pose_dim = 54
num_examples_to_generate = 16
optimizer = tf.keras.optimizers.Adam(1e-4)

# CDAE Network setup
cdae = CDAE(latent_dim)
cdae.compile(optimizer=optimizer, loss="mse")

# CDAE Network learn
start_time = time.time()
for i in range(10):
  cdae.fit(train_noisy_dataset, train_dataset, epochs=epochs, batch_size=BATCH_SIZE)
  generate_and_save_images(cdae, (i+1)*100, train_noisy[:num_examples_to_generate], train_noisy[:num_examples_to_generate], np.array(train_dataset)[:num_examples_to_generate])
  cdae.save_weights(lsd_model_weight+'/local_cdae_weights_256_latent_epoch_{}.chpt'.format((i+1)*100))
end_time = time.time()
print('time elapsed: {}s'.format(end_time-start_time))

# Pose network train data setup
latent_list = None
for i in range(len(train_dataset)//BATCH_SIZE+1):
    if latent_list is None:
        latent_list = cdae.encode(train_dataset[i*BATCH_SIZE:min((i+1)*BATCH_SIZE, len(train_dataset))])
    else:
        batch_latent_list = cdae.encode(train_dataset[i*BATCH_SIZE:min((i+1)*BATCH_SIZE, len(train_dataset))])
        latent_list = np.concatenate((latent_list, batch_latent_list), axis = 0)
latent_list = tf.convert_to_tensor(latent_list)

# Pose network setup
posenet= PoseNet(pose_dim)
posenet.compile(optimizer=optimizer, loss=tf.keras.losses.MeanAbsoluteError())

# Pose network learn
pose_net_epoch = 100
posenet.fit(latent_list, train_pose_dataset, epochs=pose_net_epoch, batch_size=BATCH_SIZE, validation_data=(cdae.encode(test_dataset),test_pose_dataset))
pose_net_epoch = 500
posenet.fit(cdae.encode(test_dataset), test_pose_dataset, epochs=pose_net_epoch, batch_size=BATCH_SIZE, validation_data=(latent_list,train_pose_dataset))

posenet.save_weights(lsd_model_weight+'local_wide_posenet_weights_256_latent_transfer_epoch_{}.chpt'.format(pose_net_epoch))