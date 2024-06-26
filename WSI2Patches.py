import os
import matplotlib.pyplot as plt
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = pow(2,40).__str__()
import cv2 
import pandas as pd
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

train_wsi_path = '/tmp/work/train_thumbnails'
train_tma_path = '/tmp/work/train_images'
train_wsi_mask_path = '/tmp/work/mask'
train_csv_path = '/tmp/work/train.csv'
index = []
indextf=[]
df = pd.DataFrame({'image_id': [], 'label': [], 'tratio':[], 'image_path':[]})
dfft = pd.DataFrame({'image_id': [], 'label': [], 'tratio':[], 'image_path':[]})

def slice_wsi(num, wsi, mask, label, image_id, n_i, t_i, b_i):
    height, width, channels = wsi.shape
    nb_rows = (height // patch_size)
    nb_cols = (width // patch_size)
    ori_patches = nb_rows*nb_cols
    rem_patches = 0
    for j in range(nb_rows):
        for i in range(nb_cols):
            box = (i*patch_size, j*patch_size, min(int((i+step)*patch_size), width), min(int((j+step)*patch_size), height))
            wsi_patch = wsi[box[1]:box[3], box[0]:box[2]]
            mask_patch = mask[box[1]:box[3], box[0]:box[2]]
            total_pixels = wsi_patch.shape[0] * wsi_patch.shape[1]
            
            red_channel = mask_patch[:, :, 0]
            red_channel = (red_channel > 0).sum()  
            img = cv2.cvtColor(wsi_patch,cv2.COLOR_RGB2GRAY)
            img_array = np.ravel(img)
            counts = np.bincount(img_array)
            most_frequent = np.max(counts)
            if most_frequent/total_pixels < 0.6:
                '''
                有腫瘤
                '''
                outputpath = f'/tf/CCC/train-{patch_size}-nn/{label}'
                if not os.path.isdir(outputpath):
                    os.makedirs(outputpath)
                cv2.imwrite(f'/tf/CCC/train-{patch_size}-nn/{label}/{t_i}.png', wsi_patch)
                df.loc[len(df)] = {'image_id': num, 'label': label, 'tratio':round(red_channel / total_pixels, 2),'image_path': f'/tf/CCC/train-{patch_size}-nn/{label}/{t_i}.png'}
                
                num+=1
                t_i+=1
                rem_patches+=1
            else:
                outputpath = f'/tf/CCC/train-{patch_size}-nn/{label}_rm'
                if not os.path.isdir(outputpath):
                    os.makedirs(outputpath)
                cv2.imwrite(f'/tf/CCC/train-{patch_size}-nn/{label}_rm/{n_i}.png', wsi_patch)
                n_i+=1
    print(f'Image:{image_id}.png Label:{label} Remain patches:{int(100*(rem_patches/ori_patches))}%')
    return num, n_i, t_i, b_i
   


def resize_image(mask, wsi):
    height, width, _ = wsi.shape
    mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_AREA)

    return mask, wsi
    

def slice_patch(num, dfs):
    n_i = 0
    b_i = 0
    for i in range(len(dfs)):
        local_df = dfs[i]
        t_i =  0
        for ind in local_df.index:
            image_id = local_df['image_id'][ind]
            image_label = local_df['label'][ind]
            wsi_path = f'{train_wsi_path}/{image_id}_thumbnail.png'
            mask_path = f'{train_wsi_mask_path}/{image_id}.png'
            if os.path.exists(mask_path):
                if os.path.exists(wsi_path):
                    mask = cv2.imread(mask_path)
                    if mask is not None:
                        wsi = cv2.imread(wsi_path)
                        if wsi is not None:
                            mask, wsi = resize_image(mask, wsi)
                            wsi = cv2.cvtColor(wsi, cv2.COLOR_BGR2RGB)
                            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2RGB)

                            num, n_i, t_i, b_i = slice_wsi(num, wsi, mask, image_label, image_id, n_i, t_i, b_i)
                    
        index.append(t_i)
        indextf.append(0)
    return num

def crop_resize(num, numft, dfs_tma):
    for i in range(len(dfs_tma)):
        local_df = dfs_tma[i]
        tft_i= indextf[i]
        for ind in local_df.index:
            image_id = local_df['image_id'][ind]
            image_label = local_df['label'][ind]
            wsi_path = f'{train_tma_path}/{image_id}.png'
            if os.path.exists(wsi_path):
                img = cv2.imread(wsi_path)
                center_x, center_y = img.shape[1] // 2, img.shape[0] // 2
                    
                if patch_size == 224:
                    crop_size = 1008
                elif patch_size == 256:
                    crop_size = 1024
                elif patch_size == 288:
                    crop_size = 1008
                elif patch_size == 384:
                    crop_size = 960
                
                left = center_x - crop_size
                top = center_y - crop_size
                right = center_x + crop_size
                bottom = center_y + crop_size
                
                img = img[top:bottom, left:right]
                    
                    
                height, width, channels = img.shape
                nb_rows = (height // patch_size)
                nb_cols = (width // patch_size)
                step=1
                for j in range(nb_rows):
                    for i in range(nb_cols):
                        box = (i*patch_size, j*patch_size, min(int((i+step)*patch_size), width), min(int((j+step)*patch_size), height))
                        wsi_patch = img[box[1]:box[3], box[0]:box[2]]
                        ftoutputpath = f'/tf/CCC/ft-{patch_size}-nn/{image_label}'
                        if not os.path.isdir(ftoutputpath):
                            os.makedirs(ftoutputpath)
                        cv2.imwrite(f'/tf/CCC/ft-{patch_size}-nn/{image_label}/{tft_i}.png', cv2.cvtColor(wsi_patch,cv2.COLOR_BGR2RGB))
                        dfft.loc[len(dfft)] = {'image_id': numft, 'label': image_label, 'tratio':1, 'image_path': f'/tf/CCC/ft-{patch_size}-nn/{image_label}/{tft_i}.png'}
                        numft+=1
                        tft_i+=1
                print(f'Image:{image_id}.png Label:{image_label} TMA')


if __name__ == '__main__':
    num=0
    train_df = pd.read_csv(train_csv_path)
    patch_size = 224
    step = 1
    numft=0
    dfs = []
    MC_df = train_df[(train_df['label'] == 'MC') & (train_df['is_tma'] == False)][['image_id', 'label']]
    dfs.append(MC_df)
    EC_df = train_df[(train_df['label'] == 'EC') & (train_df['is_tma'] == False)][['image_id', 'label']]
    dfs.append(EC_df)
    CC_df = train_df[(train_df['label'] == 'CC') & (train_df['is_tma'] == False)][['image_id', 'label']]
    dfs.append(CC_df)
    HGSC_df = train_df[(train_df['label'] == 'HGSC') & (train_df['is_tma'] == False)][['image_id', 'label']]
    dfs.append(HGSC_df)
    LGSC_df = train_df[(train_df['label'] == 'LGSC') & (train_df['is_tma'] == False)][['image_id', 'label']]
    dfs.append(LGSC_df)
    num = slice_patch(num, dfs)

    dfs_tma = []
    MC_df_tma = train_df[(train_df['label'] == 'MC') & (train_df['is_tma'] == True)][['image_id', 'label']]
    dfs_tma.append(MC_df_tma)
    EC_df_tma = train_df[(train_df['label'] == 'EC') & (train_df['is_tma'] == True)][['image_id', 'label']]
    dfs_tma.append(EC_df_tma)
    CC_df_tma = train_df[(train_df['label'] == 'CC') & (train_df['is_tma'] == True)][['image_id', 'label']]
    dfs_tma.append(CC_df_tma)
    HGSC_df_tma = train_df[(train_df['label'] == 'HGSC') & (train_df['is_tma'] == True)][['image_id', 'label']]
    dfs_tma.append(HGSC_df_tma)
    LGSC_df_tma = train_df[(train_df['label'] == 'LGSC') & (train_df['is_tma'] == True)][['image_id', 'label']]
    dfs_tma.append(LGSC_df_tma)
    crop_resize(num, numft, dfs_tma)
    df.to_csv(f'/tf/CCC/train-{patch_size}-nn/patch_out.csv', index=False)
    dfft.to_csv(f'/tf/CCC/ft-{patch_size}-nn/patch_out_ft.csv', index=False)
