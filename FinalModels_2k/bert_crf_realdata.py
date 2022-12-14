# -*- coding: utf-8 -*-
"""BERT_CRF_realData.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1qpRu3zISsWHJEZT-Uqmjy3DXH_pvgK4F
"""

import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_hub as hub

import keras 
from keras.models import Sequential,Model
from keras.layers import LSTM,Bidirectional,Dense,Input,Embedding,TimeDistributed
from keras.callbacks import EarlyStopping, ModelCheckpoint

import nltk
import sklearn
import scipy.stats
from sklearn.metrics import make_scorer
from sklearn.model_selection import cross_val_score
from nltk.tokenize import word_tokenize
import numpy as np

from google.colab import drive,files
drive.mount("/content/drive")
dataM='/content/drive/My Drive/Colab Notebooks/MODELS/'
filepath = dataM+'BERT_CRF.ml'

!pip install tensorflow_text

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

!pip install tf2crf

from tf2crf import CRF 
from tf2crf import ModelWithCRFLoss

!cp -rf drive/MyDrive/job_20k.json /content/

import pandas as pd
import json
path_to_json = 'job_20k.json'
df  = pd.read_json(path_to_json,lines=True)
df.head().T

df['clean_descrition'] = df['clean_descrition'].str.replace(r'[^\w\s]+', ' ')
df['clean_descrition'] = df['clean_descrition'].apply(lambda x: ' '.join(x.split()[:128]))
df['clean_descrition'][1]

import pandas as pd
import json
path_to_json = 'job_20k.json'
df  = pd.read_json(path_to_json,lines=True)
df.head().T

jobs = list(df.clean_descrition)
def convert_to_list_then_dict(df_column= None, key_value=str):
    value_list = list(df_column)
    _ = list(set([item for value_list in value_list for item in value_list]))
    return dict.fromkeys(_, key_value)

org = convert_to_list_then_dict(df_column=df.organization_list, key_value='C')
skill = convert_to_list_then_dict(df_column=df.skill_list, key_value='S')
job = convert_to_list_then_dict(df_column=df.job_title_list, key_value='J')

XTr= jobs[:1500]
XVal= jobs[1500:2000]
org_b = org
skills_b = skill
jobs_b = job

def make(X,org_b,skills_b,jobs_b):
  big=[]
  for sentence in X:
    token=word_tokenize(sentence)
    small=[]
    token_t=nltk.pos_tag(token)
    for f,s in token_t:
      tag='O'
      if f.lower() in org_b:
        tag=org_b[f.lower()]
      if f.lower() in skills_b:
        tag=skills_b[f.lower()]
      if f.lower() in jobs_b:
        tag=jobs_b[f.lower()]
      small.append((f,s,tag))
    big.append(small)
  return big
  
XTr_=make(XTr,org_b,skills_b,jobs_b)
XVal_=make(XVal,org_b,skills_b,jobs_b)

msgLen=128

def fixMsg(X):
  global msgLen
  Xc=[]
  for i in range(len(X)):
    if len(X[i])<msgLen:
      Xc.append(X[i].copy())
      while len(Xc[-1])<msgLen:
        Xc[-1].append(('UNK','UNK','UNK'))
    elif len(X[i])>msgLen:
      Xc.append(X[i].copy())
      temp=Xc[-1].copy()
      del Xc[-1]
      lb=0;chunk=msgLen
      while lb<len(temp):
        split=[]
        for j in range(lb,lb+chunk):
          if j<len(temp):
            split.append(temp[j])
          else:
            split.append(('UNK','UNK','UNK'))
        Xc.append(split)
        assert(len(split)==msgLen)
        lb+=chunk
  return Xc

XTr_t=fixMsg(XTr_)
XVal_t=fixMsg(XVal_)

for x in XTr_t:
  if len(x)!=msgLen:
    print(len(x))
print(XTr_t[0])
for x in XVal_t:
  assert(len(x)==msgLen)
print(XVal_t[0])

dict_={}
dict_1={}
token=1;token1=0
for x in XTr_t:
  for a,b,c in x:
    if a not in dict_:
      dict_[a]=token
      token=token+1
    if c not in dict_1:
      if c=='K':
        print(a,b,c)
      dict_1[c]=token1
      token1=token1+1
for x in XVal_t:
  for a,b,c in x:
    if a not in dict_:
      dict_[a]=token
      token=token+1
    if c not in dict_1:
      dict_1[c]=token1
      token1=token1+1
print('No of tokens words[{}] labels[{}]'.format(token,token1))

def bertCreate(X):
  temp=[]
  for sentence in X:
    s=''
    first=True
    for element in sentence:
      if first:
        first=False
        s=element[0]
      else:
        s=s+' '+element[0]
    temp.append(s)
  return np.array(temp)

XTr_fin=bertCreate(XTr_t)
XVal_fin=bertCreate(XVal_t)

yTr=np.array([[dict_1[element[2]] for element in sentence] for sentence in XTr_t])
yVal=np.array([[dict_1[element[2]] for element in sentence] for sentence in XVal_t])

import tensorflow_text as text
preprocessor = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_en_cased_preprocess/3")

text_preprocessed = preprocessor(np.array(XTr_fin[:2]))

print(f'Keys       : {list(text_preprocessed.keys())}')
print(f'Shape      : {text_preprocessed["input_word_ids"].shape}')
print(f'Word Ids   : {text_preprocessed["input_word_ids"][0, :12]}')
print(f'Input Mask : {text_preprocessed["input_mask"][0, :12]}')
print(f'Type Ids   : {text_preprocessed["input_type_ids"][0, :12]}')

# https://tfhub.dev/tensorflow/bert_en_cased_L-12_H-768_A-12/4
# https://tfhub.dev/tensorflow/bert_en_cased_preprocess/3

bert_layer = hub.KerasLayer('https://tfhub.dev/tensorflow/bert_en_cased_L-12_H-768_A-12/4', trainable=False)

input=Input(shape=(), dtype=tf.string)
model0=preprocessor(input)
seq_op=bert_layer(model0)['sequence_output']
model0=Model(input,seq_op)
model0.summary()

XTr_fin=model0.predict(XTr_fin)
XVal_fin=model0.predict(XVal_fin)

print(XTr_fin.shape,XVal_fin.shape,type(XTr_fin),type(XVal_fin))

print(yTr.shape,yVal.shape,type(yTr),type(yVal))

input=Input(shape=(XTr_fin.shape[1],XTr_fin.shape[2]))
output=CRF(units=token1)(input)
mo=Model(input,output)
mo.summary()

model1=ModelWithCRFLoss(mo,sparse_target=True)
model1.compile(optimizer ='rmsprop')

es = EarlyStopping(monitor = "val_loss_val", mode = "min", verbose = True, restore_best_weights=True, patience = 1)
cp = ModelCheckpoint(filepath,monitor="val_loss_val",mode = "min",verbose=True,save_best_only=True)

history = model1.fit(XTr_fin,yTr,validation_data=[XVal_fin,yVal],epochs=15,batch_size=100,callbacks=[cp,es])

model1.load_weights(filepath)

import matplotlib.pyplot as plt

plt.rcParams["figure.figsize"] = (16,8)
plt.plot(history.history['val_loss_val'])
plt.plot(history.history['loss'])
plt.xlabel('Epochs ->')
plt.ylabel('Losses ->')
plt.title('Losses v/s epochs.')
plt.legend(['Val Loss','Train Loss'])
plt.show()

dict_1R={}
for k,v in dict_1.items():
  dict_1R[v]=k

labels_=model1.predict(XVal_fin)
i=0 # i-th example from val dataset.
cnt=0
print()
for x in XVal_[0]:
  print('{} {}'.format(x[0],dict_1R[labels_[i][cnt]]))
  cnt+=1
  if cnt>10:
    break

dict_1

!pip install sklearn-crfsuite

import sklearn_crfsuite
from sklearn_crfsuite import scorers
from sklearn_crfsuite import metrics

def labelIt(yVal):
  yVal_lis=[]
  for y1 in yVal:
    temp=[]
    for y2 in y1:
      temp.append(dict_1R[y2])
    yVal_lis.append(temp)
  return yVal_lis 

yVal_=labelIt(yVal)
yPred_=labelIt(labels_)
labls=['C','J','S','O','UNK']
metrics.flat_f1_score(yVal_,yPred_,average='weighted',labels=labls)

pip install -U 'scikit-learn<0.24'

print(metrics.flat_classification_report(yVal_,yPred_,labels=labls,digits=3))