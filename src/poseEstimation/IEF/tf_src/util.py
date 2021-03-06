import numpy as np
import tensorflow as tf
from scipy.stats import multivariate_normal
import os
import logging
import cv2

C = 3.50666662e-3

np.set_printoptions(threshold=np.nan)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

fh = logging.FileHandler('log.txt')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

jointNameITOP = ['HEAD', 'NECK', 'LEFT_SHOULDER', 'RIGHT_SHOULDER', \
                'LEFT_ELBOW', 'RIGHT_ELBOW', 'LEFT_HAND', 'RIGHT_HAND', \
                'TORSO', 'LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', \
                'RIGHT_KNEE', 'LEFT_FOOT', 'RIGHT_FOOT']

def get_results(x=None, y=None, yt=None, show=True, dists=None, per_joint=False):
    if dists is None:
        dists = get_distances(x, y, yt)*100
    if show == True:
        if per_joint:
            for i in range(dists.shape[1]):
                logger.debug('%s: ', jointNameITOP[i])
                logger.debug('average distance: %f cm', np.mean(dists[:, i]))
                logger.debug('5cm accuracy: %f', np.sum(dists[:, i] < 5)/ \
                    float(dists.shape[0]))
                logger.debug('10cm accuracy: %f', np.sum(dists[:, i] < 10)/ \
                    float(dists.shape[0]))
                logger.debug('15cm accuracy: %f', np.sum(dists[:, i] < 15)/ \
                    float(dists.shape[0]))
        else:
            logger.debug('average distance: %f cm', np.mean(dists))
            logger.debug('5cm accuracy: %f', np.sum(dists < 5)/ \
                float(dists.shape[0]*dists.shape[1]))
            logger.debug('10cm accuracy: %f', np.sum(dists < 10)/ \
                float(dists.shape[0]*dists.shape[1]))
            logger.debug('15cm accuracy: %f', np.sum(dists < 15)/ \
                float(dists.shape[0]*dists.shape[1]))
    return dists

def pixel2world(pixel, C, H, W):
    world = np.empty(pixel.shape)
    world[:, 2] = pixel[:, 2]
    world[:, 0] = (pixel[:, 0]-W/2.0)*C*pixel[:, 2]
    world[:, 1] = -(pixel[:, 1]-H/2.0)*C*pixel[:, 2]
    return world

def get_distances(imgs, joints, joints_pred):
    assert joints.shape == joints_pred.shape
    dists = np.zeros((joints.shape[:2]))
    largeNum = np.mean(imgs[imgs != 0].astype(np.float64))
    if largeNum > 4:
        print 'largeNum: %f' % largeNum
        assert False
    H = 224
    W = 224

    for i in range(joints.shape[0]):
        coor = joints[i].copy().astype(int)
        coor_pred = joints_pred[i].copy().astype(int)
        coor[:, 0] = np.clip(coor[:, 0], 0, W-1)
        coor[:, 1] = np.clip(coor[:, 1], 0, H-1)
        coor_pred[:, 0] = np.clip(coor_pred[:, 0], 0, W-1)
        coor_pred[:, 1] = np.clip(coor_pred[:, 1], 0, H-1)

        z = imgs[i][tuple(np.fliplr(coor).T)]
        z_pred = imgs[i][tuple(np.fliplr(coor_pred).T)]
        z[z == 0] = largeNum
        z_pred[z_pred == 0] = largeNum

        p1 = pixel2world(np.hstack((joints[i], z[:, np.newaxis])), C, H, W)
        p2 = pixel2world(np.hstack((joints_pred[i], z_pred[:, np.newaxis])), \
                         C, H, W)

        dists[i] = np.sqrt(np.sum((p1-p2)**2, axis=1))
    return dists

def resize(data_dir, img_height, img_width):
    depth_people = [data_dir + d for d in os.listdir(data_dir) if d.find('depth') != -1]
    for f in depth_people:
        logger.debug('Loading %d', f)
        images = np.load(f)
        images_new = np.zeros((len(images), img_height, img_width))
        for i in range(len(images)):
            if i % 100 == 0:
                logger.debug('Processed %d/%d', i, len(images))
            images_new[i] = cv2.resize(images[i], (img_height, img_width))
        np.save(f, images_new)

def load_data(data_root, view, small_data=False):
    X_train, y_train, X_val, y_val = None, None, None, None

    X_train = np.load(data_root+'depth_'+view+'_train.npy')
    y_train = np.load(data_root+'joint_'+view+'_train.npy')
    X_val = np.load(data_root+'depth_'+view+'_val.npy')
    y_val = np.load(data_root+'joint_'+view+'_val.npy')

    '''
    for i in range(X_train.shape[0]):
        img = X_train[i]
        img = (img-np.amin(img))*255.0/(np.amax(img)-np.amin(img))
        img = img.astype(np.uint8)
        #img = cv2.equalizeHist(X_train[i].astype(np.uint8))
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        for j in range(y_train.shape[1]):
            cv2.circle(img, tuple(y_train[i, j, :2].astype(np.uint16)), 2, (255, 0, 0), -1)
        cv2.imshow('img', img)
        cv2.waitKey(0)
    '''

    # col = [1, 2, 0]
    # y_train = y_train[:, :, col]
    # y_val = y_val[:, :, col]
    #print np.mean(X_train), np.mean(X_train[X_train != 0])

    if np.mean(X_train[X_train != 0].astype(np.float64)) > 100:
        print 'ops, mean = %f' % np.mean(X_train[X_train != 0].astype(np.float64))
        X_train /= 1000.0
        X_val /= 1000.0

    if small_data:
        rand = np.random.randint(0, X_train.shape[0], 23)
        return X_train[rand], y_train[rand, :, :2], X_val[500:523], \
            y_val[500:523, :, :2]
    else:
        return X_train, y_train[:, :, :2], X_val, y_val[:, :, :2]


def visualizeImgJointsEps(imgs, joints=None, eps=None, name='img', write=False, show=False):
    for i in range(imgs.shape[0]):
        #cv2.normalize(imgs[i], imgs[i], 0, 255, cv2.NORM_MINMAX)
        imgs[i] = (imgs[i]-np.amin(imgs[i]))*255.0/(np.amax(imgs[i])-np.amin(imgs[i]))
        img = cv2.equalizeHist(imgs[i].astype(np.uint8))
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        img_corrected = img.copy()

        if joints is not None:
            for j in range(joints.shape[1]):
                cv2.circle(img, tuple(joints[i, j, :2].astype(np.uint16)), \
                    2, (255, 0, 0), -1)

        if (joints is not None) and (eps is not None):
            for j in range(joints.shape[1]):
                joints_corrected = joints[i, j] + eps[i, j]
                cv2.circle(img_corrected, \
                    tuple(joints_corrected.astype(np.uint16)), \
                    2, (255, 0, 0), -1)

        if write:
            if not os.path.isdir('out'):
                os.makedirs('out')
            cv2.imwrite('out/'+name+'_'+str(i)+'.jpg', img_corrected)
        if show:
            cv2.imshow(name, img)
            cv2.imshow(name+'_corrected', img_corrected)
            cv2.waitKey(0)
    cv2.destroyAllWindows()

def visualizeImgHmsEps(x, yt, eps, name='img'):
    # 224 x 224 x 16
    cv2.normalize(x[:, :, 0], x[:, :, 0], 0, 255, cv2.NORM_MINMAX)
    img = cv2.equalizeHist(x[:, :, 0].astype(np.uint8))
    cv2.imshow(name, img)

    hms = np.sum(x[:, :, 1:], axis=2)
    cv2.normalize(hms, hms, 0, 255, cv2.NORM_MINMAX)
    hms = cv2.equalizeHist(hms.astype(np.uint8))
    hms = cv2.cvtColor(hms, cv2.COLOR_GRAY2RGB)
    for i, e in enumerate(eps):
        cv2.line(hms, tuple(yt[i].astype(np.uint16)), \
            tuple((yt[i]+e).astype(np.uint16)), (0, 0, 255), 2)

    cv2.imshow(name+'-hms', hms)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def world2pixel(coordW, W=320, H=240, C=3.51e-3):
    coordP = np.zeros(coordW.shape)
    coordP[:,:,0] = coordW[:,:,0] / (coordW[:,:,2]*C) + 0.5 * W
    coordP[:,:,1] = -(coordW[:,:,1] / (coordW[:,:,2]*C)) + 0.5 * H
    coordP[:,:,2] = coordW[:,:,2]
    return coordP

def create_single_heatmap(H, W):
    '''
    Creates a single heatmap

    :param cov: matrix as a python list
    :param mean: location of heatmap center as length 2 python list
    :returns hm: (cnn_input_dim1*2, cnn_input_dim2*2) grayscale heatmap
    '''
    cov = [[50, 0], [0, 50]]
    mean = [H, W]
    big_dim1, big_dim2 = H*2, W*2
    pair = np.nonzero(np.ones((big_dim1, big_dim2)))
    hm_index = np.array(zip(pair[0],pair[1])).reshape(big_dim1, big_dim2, 2)
    hm = multivariate_normal.pdf(hm_index, mean, cov)
    scale = np.amax(hm) - np.amin(hm)
    hm /= scale

    return hm

def joint_to_hm(joints, num_joints, hm, img_height=224, img_width=224):
    N = joints.shape[0]
    heat_maps = np.zeros((N, img_height, img_width, num_joints))

    for i in range(N):
        for j in range(num_joints):
            dim1_start = img_height - joints[i, j, 1]
            dim1_end = dim1_start + img_height
            dim2_start = img_width - joints[i, j, 0]
            dim2_end = dim2_start + img_width

            heat_map = hm[dim1_start:dim1_end, dim2_start:dim2_end]
            if heat_map.shape == heat_maps[i, :, :, j].shape:
                heat_maps[i, :, :, j] = heat_map

    return heat_maps

def add_hms(images, yt, num_joints, hm, num_channel=1, H=240.0, W=320.0):
    # x_batch = add_hms(x_batch, yt, num_joints, hm) # e.g. 60 x 16 x 224 x 224
    # x_batch = np.swapaxes(np.swapaxes(x_batch, 1, 2), 2, 3) # e.g. 60 x 224 x 224 x 16

    N, img_height, img_width = images.shape
    out = np.empty((N, img_height, img_width, num_channel+num_joints))
    out[:, :, :, 0] = images
    out[:, :, :, 1:] = joint_to_hm(yt[:, :, :2], num_joints, hm)

    return out

def get_bounded_correction(y, yt, num_coords, L=None):
    u = y - yt
    u_norm = np.sqrt(np.sum(u**2, axis=2)).reshape(u.shape[0], u.shape[1], 1)
    mask = np.array(u_norm == 0, dtype=int)
    u_norm += mask
    unit = u/u_norm
    correction = np.zeros(unit.shape)
    if L is not None:
        u_norm = np.minimum(L, u_norm)
    correction = unit*u_norm

    return correction

def get_batch(X, y, yt, start_idx, end_idx, num_joints, hm):
    x_batch = X[start_idx:end_idx]
    y_batch = y[start_idx:end_idx]
    yt_batch = yt[start_idx:end_idx]
    x_batch = add_hms(x_batch, yt_batch, num_joints, hm)
    # y_batch = world2pixel(y_batch)[:,:,:2] # use 2D pixel joints
    # yt_batch = world2pixel(yt_batch)[:,:,:2]
    eps_batch = get_bounded_correction(y_batch, yt_batch, num_coords=2, L=20)
    #for i in range(x_batch.shape[0]):
    #    visualizeImgHmsEps(np.copy(x_batch[i]), yt_batch[i], eps_batch[i])
    return x_batch, eps_batch

def alexNet(x, y, keep_prob, n_outputs, input_img_size):
    # Network Parameters
    W = {}
    b = {}

    x_img = tf.reshape(x, shape=[-1,input_img_size,input_img_size,1])

    W['c1'] = tf.Variable(tf.truncated_normal([11, 11, 1, 64], stddev=0.1))
    b['c1'] = tf.Variable(tf.constant(0.1, shape=[64]))
    conv1 = tf.nn.bias_add(tf.nn.conv2d(x_img, W['c1'], strides=[1,4,4,1], padding='SAME'), b['c1'])
    conv1 = tf.nn.relu(conv1)
    conv1 = tf.nn.max_pool(conv1, ksize=[1,3,3,1], strides=[1,2,2,1], padding='SAME')
    # conv1 = (29,29,64)

    W['c2'] = tf.Variable(tf.truncated_normal([5, 5, 64, 192], stddev=0.1))
    b['c2'] = tf.Variable(tf.constant(0.1, shape=[192]))
    conv2 = tf.nn.bias_add(tf.nn.conv2d(conv1, W['c2'], strides=[1,1,1,1], padding='SAME'), b['c2'])
    conv2 = tf.nn.relu(conv2)
    conv2 = tf.nn.max_pool(conv2, ksize=[1,3,3,1], strides=[1,2,2,1], padding='SAME')
    # conv2 = (15, 15, 192)

    W['c3'] = tf.Variable(tf.truncated_normal([3, 3, 192, 384], stddev=0.1))
    b['c3'] = tf.Variable(tf.constant(0.1, shape=[384]))
    conv3 = tf.nn.bias_add(tf.nn.conv2d(conv2, W['c3'], strides=[1,1,1,1], padding='SAME'), b['c3'])
    conv3 = tf.nn.relu(conv3)
    # conv3 = (15, 15, 384)

    W['c4'] = tf.Variable(tf.truncated_normal([3, 3, 384, 256], stddev=0.1))
    b['c4'] = tf.Variable(tf.constant(0.1, shape=[256]))
    conv4 = tf.nn.bias_add(tf.nn.conv2d(conv3, W['c4'], strides=[1,1,1,1], padding='SAME'), b['c4'])
    conv4 = tf.nn.relu(conv4)
    # conv4 = (15,15,256)

    W['c5'] = tf.Variable(tf.truncated_normal([3, 3, 256, 256], stddev=0.1))
    b['c5'] = tf.Variable(tf.constant(0.1, shape=[256]))
    conv5 = tf.nn.bias_add(tf.nn.conv2d(conv4, W['c5'], strides=[1,1,1,1], padding='SAME'), b['c5'])
    conv5 = tf.nn.relu(conv5)
    conv5 = tf.nn.max_pool(conv5, ksize=[1,3,3,1], strides=[1,2,2,1], padding='SAME')
    # conv5 = (8,8,256)

    # Dense Layers
    W['d1'] = tf.Variable(tf.truncated_normal([8*8*256, 4096], stddev=0.1))
    b['d1'] = tf.Variable(tf.constant(0.1, shape=[4096]))
    dense1 = tf.reshape(conv5, [-1, W['d1'].get_shape().as_list()[0]])
    dense1 = tf.nn.relu(tf.add(tf.matmul(dense1, W['d1']), b['d1']))
    dense1 = tf.nn.dropout(dense1, keep_prob)

    W['d2'] = tf.Variable(tf.truncated_normal([4096, 4096], stddev=0.1))
    b['d2'] = tf.Variable(tf.constant(0.1, shape=[4096]))
    dense2 = tf.nn.relu(tf.add(tf.matmul(dense1, W['d2']), b['d2']))
    dense2 = tf.nn.dropout(dense2, keep_prob)

    W['out'] = tf.Variable(tf.truncated_normal([4096, n_outputs], stddev=0.1))
    b['out'] = tf.Variable(tf.constant(0.1, shape=[n_outputs]))

    y_hat = tf.add(tf.matmul(dense2, W['out']), b['out'])

    return y_hat

def vgg19(x, y, keep_prob, n_outputs, input_img_size, num_channel):
    W = {}
    b = {}
    layer = {}

    # Make x a "square" image. Currently it's a vector
    x_img = tf.reshape(x, shape=[-1,input_img_size,input_img_size,num_channel])

    # Weight initialization
    WEIGHT_STD = 0.05

    W['c1_1'] = tf.Variable(tf.truncated_normal([3,3,16,64], stddev=WEIGHT_STD))
    b['c1_1'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[64]))
    layer['c1_1'] = tf.nn.bias_add(tf.nn.conv2d(x_img, W['c1_1'], strides=[1,1,1,1], padding='SAME'), b['c1_1'])
    layer['c1_1'] = tf.nn.relu(layer['c1_1'])
    # conv1 output = (224,224,64)

    W['c1_2'] = tf.Variable(tf.truncated_normal([3,3,64,64], stddev=WEIGHT_STD))
    b['c1_2'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[64]))
    layer['c1_2'] = tf.nn.bias_add(tf.nn.conv2d(layer['c1_1'], W['c1_2'], strides=[1,1,1,1], padding='SAME'), b['c1_2'])
    layer['c1_2'] = tf.nn.relu(layer['c1_2'])
    layer['c1_2'] = tf.nn.max_pool(layer['c1_2'], ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')
    # layer['c1_2'] output = (112,112,64)

    W['c2_1'] = tf.Variable(tf.truncated_normal([3,3,64,128], stddev=WEIGHT_STD))
    b['c2_1'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[128]))
    layer['c2_1'] = tf.nn.bias_add(tf.nn.conv2d(layer['c1_2'], W['c2_1'], strides=[1,1,1,1], padding='SAME'), b['c2_1'])
    layer['c2_1'] = tf.nn.relu(layer['c2_1'])
    # layer['c2_1'] output = (224,224,64)

    W['c2_2'] = tf.Variable(tf.truncated_normal([3,3,128,128], stddev=WEIGHT_STD))
    b['c2_2'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[128]))
    layer['c2_2'] = tf.nn.bias_add(tf.nn.conv2d(layer['c2_1'], W['c2_2'], strides=[1,1,1,1], padding='SAME'), b['c2_2'])
    layer['c2_2'] = tf.nn.relu(layer['c2_2'])
    layer['c2_2'] = tf.nn.max_pool(layer['c2_2'], ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')
    # layer['c2_2'] output = (56,56,64)

    W['c3_1'] = tf.Variable(tf.truncated_normal([3,3,128,256], stddev=WEIGHT_STD))
    b['c3_1'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[256]))
    layer['c3_1'] = tf.nn.bias_add(tf.nn.conv2d(layer['c2_2'], W['c3_1'], strides=[1,1,1,1], padding='SAME'), b['c3_1'])
    layer['c3_1'] = tf.nn.relu(layer['c3_1'])

    W['c3_2'] = tf.Variable(tf.truncated_normal([3,3,256,256], stddev=WEIGHT_STD))
    b['c3_2'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[256]))
    layer['c3_2'] = tf.nn.bias_add(tf.nn.conv2d(layer['c3_1'], W['c3_2'], strides=[1,1,1,1], padding='SAME'), b['c3_2'])
    layer['c3_2'] = tf.nn.relu(layer['c3_2'])

    W['c3_3'] = tf.Variable(tf.truncated_normal([3,3,256,256], stddev=WEIGHT_STD))
    b['c3_3'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[256]))
    layer['c3_3'] = tf.nn.bias_add(tf.nn.conv2d(layer['c3_2'], W['c3_3'], strides=[1,1,1,1], padding='SAME'), b['c3_3'])
    layer['c3_3'] = tf.nn.relu(layer['c3_3'])

    W['c3_4'] = tf.Variable(tf.truncated_normal([3,3,256,256], stddev=WEIGHT_STD))
    b['c3_4'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[256]))
    layer['c3_4'] = tf.nn.bias_add(tf.nn.conv2d(layer['c3_3'], W['c3_4'], strides=[1,1,1,1], padding='SAME'), b['c3_4'])
    layer['c3_4'] = tf.nn.relu(layer['c3_4'])
    layer['c3_4'] = tf.nn.max_pool(layer['c3_4'], ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')
    # layer['c3_4'] = (28,28,256)

    W['c4_1'] = tf.Variable(tf.truncated_normal([3,3,256,512], stddev=WEIGHT_STD))
    b['c4_1'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c4_1'] = tf.nn.bias_add(tf.nn.conv2d(layer['c3_4'], W['c4_1'], strides=[1,1,1,1], padding='SAME'), b['c4_1'])
    layer['c4_1'] = tf.nn.relu(layer['c4_1'])

    W['c4_2'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c4_2'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c4_2'] = tf.nn.bias_add(tf.nn.conv2d(layer['c4_1'], W['c4_2'], strides=[1,1,1,1], padding='SAME'), b['c4_2'])
    layer['c4_2'] = tf.nn.relu(layer['c4_2'])

    W['c4_3'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c4_3'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c4_3'] = tf.nn.bias_add(tf.nn.conv2d(layer['c4_2'], W['c4_3'], strides=[1,1,1,1], padding='SAME'), b['c4_3'])
    layer['c4_3'] = tf.nn.relu(layer['c4_3'])

    W['c4_4'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c4_4'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c4_4'] = tf.nn.bias_add(tf.nn.conv2d(layer['c4_3'], W['c4_4'], strides=[1,1,1,1], padding='SAME'), b['c4_4'])
    layer['c4_4'] = tf.nn.relu(layer['c4_4'])
    layer['c4_4'] = tf.nn.max_pool(layer['c4_4'], ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')
    # layer['c4_4'] = (14,14,512)

    W['c5_1'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c5_1'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c5_1'] = tf.nn.bias_add(tf.nn.conv2d(layer['c4_4'], W['c5_1'], strides=[1,1,1,1], padding='SAME'), b['c5_1'])
    layer['c5_1'] = tf.nn.relu(layer['c5_1'])

    W['c5_2'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c5_2'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c5_2'] = tf.nn.bias_add(tf.nn.conv2d(layer['c5_1'], W['c5_2'], strides=[1,1,1,1], padding='SAME'), b['c5_2'])
    layer['c5_2'] = tf.nn.relu(layer['c5_2'])

    W['c5_3'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c5_3'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c5_3'] = tf.nn.bias_add(tf.nn.conv2d(layer['c5_2'], W['c5_3'], strides=[1,1,1,1], padding='SAME'), b['c5_3'])
    layer['c5_3'] = tf.nn.relu(layer['c5_3'])

    W['c5_4'] = tf.Variable(tf.truncated_normal([3,3,512,512], stddev=WEIGHT_STD))
    b['c5_4'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[512]))
    layer['c5_4'] = tf.nn.bias_add(tf.nn.conv2d(layer['c5_3'], W['c5_4'], strides=[1,1,1,1], padding='SAME'), b['c5_4'])
    layer['c5_4'] = tf.nn.relu(layer['c5_4'])
    layer['c5_4'] = tf.nn.max_pool(layer['c5_4'], ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')
    # layer['c5_4'] = (7,7,512)

    W['d1'] = tf.Variable(tf.truncated_normal([7*7*512, 4096], stddev=WEIGHT_STD))
    b['d1'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[4096]))
    layer['d1'] = tf.reshape(layer['c5_4'], [-1, W['d1'].get_shape().as_list()[0]])
    layer['d1'] = tf.nn.relu(tf.nn.bias_add(tf.matmul(layer['d1'], W['d1']), b['d1']))
    layer['d1'] = tf.nn.dropout(layer['d1'], keep_prob)

    W['d2'] = tf.Variable(tf.truncated_normal([4096, 4096], stddev=WEIGHT_STD))
    b['d2'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[4096]))
    layer['d2'] = tf.nn.relu(tf.nn.bias_add(tf.matmul(layer['d1'], W['d2']), b['d2']))
    layer['d2'] = tf.nn.dropout(layer['d2'], keep_prob)

    W['out'] = tf.Variable(tf.truncated_normal([4096, n_outputs], stddev=WEIGHT_STD))
    b['out'] = tf.Variable(tf.constant(WEIGHT_STD, shape=[n_outputs]))
    #layer['out'] = tf.reshape(layer['c5_4'], [-1, W['out'].get_shape().as_list()[0]])
    y_hat = tf.nn.bias_add(tf.matmul(layer['d1'], W['out']), b['out'])

    return y_hat

def save_data(data_root, out_dir, view, person_id_list, d_type):
    depth_view = []
    joint_view = []
    for i in person_id_list:
        index = str(i).zfill(2)
        logger.debug('Loading %s', data_root+index)
        depth = np.load(data_root + index + '_depth_' + view + '.npy')
        joint = np.load(data_root + index + '_joints_' + view + '.npy')
        depth_view.append(depth)
        joint_view.append(joint)
    depth_view = np.vstack(depth_view)
    joint_view = np.vstack(joint_view)
    np.save(out_dir + 'depth_' + view + '_' + d_type + '.npy', depth_view)
    np.save(out_dir + 'joint_' + view + '_' + d_type + '.npy', joint_view)

def main_0():
    a = np.load('/mnt0/data/ITOP/out/00_depth_top.npy')
    b = np.load('/mnt0/alan/healthcare/src/poseEstimation/IEF/tf_src/results/pred_2d_val_top.npy')

    np.save('/mnt0/alan/healthcare/src/poseEstimation/IEF/tf_src/results/depth_top_small.npy', a[:1000])
    np.save('/mnt0/alan/healthcare/src/poseEstimation/IEF/tf_src/results/pred_2d_val_top_small.npy', b[:1000])

def main_1():
    id = 0
    view = 'top'
    data_root = '/mnt0/alan/healthcare/src/poseEstimation/RTW/data_EVAL'
    out_dir = '/mnt0/alan/healthcare/src/poseEstimation/IEF/tf_data_EVAL'
    nJoints = 12
    scale = True
    tl = (48, 16) # x, y

    I_train, I_val = np.empty((0, 224, 224), np.float16), \
        np.empty((0, 224, 224), np.float16)
    joints_train, joints_val = np.empty((0, nJoints, 3)), \
        np.empty((0, nJoints, 3))

    depth = np.load(data_root + '/I.npy')
    mask = np.load(data_root + '/I_mask.npy')
    joints = np.load(data_root + '/joints.npy')
    depth *= mask

    depth_resize = np.empty((depth.shape[0], 224, 224))
    if scale:
        joints[:, :, 0] *= 224.0/320
        joints[:, :, 1] *= 224.0/240
        for j, img in enumerate(depth):
            depth_resize[j] = cv2.resize(img, (224, 224))
    else:
        joints[:, :, 0] -= tl[0]
        joints[:, :, 1] -= tl[1]
        for j, img in enumerate(depth):
            depth_resize[j] = img[tl[1]:(tl[1]+224), tl[0]:(tl[0]+224)]

    nTest = depth_resize.shape[0]*0.3
    I_val = depth_resize[:nTest]
    I_train = depth_resize[nTest:]
    joints_val = joints[:nTest]
    joints_train = joints[nTest:]

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    np.save(out_dir + '/I_train.npy', I_train)
    np.save(out_dir + '/joints_train.npy', joints_train)
    np.save(out_dir + '/I_val.npy', I_val)
    np.save(out_dir + '/joints_val.npy', joints_val)

def main():
    id = 0
    view = 'top'
    data_root = '/mnt0/data/ITOP/out/'
    out_dir = '../tf_data/'
    nJoints = 15
    scale = True
    tl = (48, 16) # x, y

    I_train, I_val = np.empty((0, 224, 224), np.float16), \
        np.empty((0, 224, 224), np.float16)
    joints_train, joints_val = np.empty((0, nJoints, 3)), \
        np.empty((0, nJoints, 3))

    trainTestITOP = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0]

    for i, isTest in enumerate(trainTestITOP): #test
        index = str(i).zfill(2)
        depth = np.load(data_root + index + '_depth_' + view + '.npy')
        labels = np.load(data_root + index + '_predicts_' + view + '.npy')
        joints = np.load(data_root + index + '_joints_' + view + '.npy')

        labels[labels >= 0] = 1
        labels[labels < 0] = 0
        depth *= labels
        depth /= 1000.0
        joints = joints[:, :, :3]
        joints[:, :, 2] /= 1000.0

        depth_resize = np.empty((depth.shape[0], 224, 224))
        if scale:
            joints[:, :, 0] *= 224.0/320
            joints[:, :, 1] *= 224.0/240
            for j, img in enumerate(depth):
                depth_resize[j] = cv2.resize(img, (224, 224))
        else:
            joints[:, :, 0] -= tl[0]
            joints[:, :, 1] -= tl[1]
            for j, img in enumerate(depth):
                depth_resize[j] = img[tl[1]:(tl[1]+224), tl[0]:(tl[0]+224)]

        #visualizeImgJointsEps(depth_resize.copy(), joints.copy())

        if isTest == 0:
            I_train = np.append(I_train, depth_resize, axis=0).astype('float16')
            joints_train = np.append(joints_train, joints, axis=0)
        else:
            I_val = np.append(I_val, depth_resize, axis=0).astype('float16')
            joints_val = np.append(joints_val, joints, axis=0)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    np.save(out_dir + 'depth_' + view + '_train.npy', I_train)
    np.save(out_dir + 'joint_' + view + '_train.npy', joints_train)
    np.save(out_dir + 'depth_' + view + '_val.npy', I_val)
    np.save(out_dir + 'joint_' + view + '_val.npy', joints_val)

if __name__ == "__main__":
    main_1()
