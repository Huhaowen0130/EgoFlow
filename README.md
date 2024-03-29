# EgoFlow: detect if a person is looking at me with RGB and corresponding optical-flow sequences.

### Introduction
This is a method proposed for [2022 Ego4D Looking-at-Me Challenge](https://eval.ai/web/challenges/challenge-page/1624/overview), utilizing [Ego4D dataset](https://ego4d-data.org/docs/challenge/#dataset) and an optical flow dataset, this dataset is created with the RGB images in Ego4D by a neural network called [FlowFormer](https://github.com/drinkingcoder/FlowFormer-Official).

### Installation
```
conda create -n egoflow python=3.8 
conda activate egoflow
conda install pytorch=1.7.1 torchvision=0.8.2 cudatoolkit=11.0
pip install -r requirements.txt
```

### Model
1. FlowFormer

Create a folder
```
mkdir checkpoints
```
and put [sintel.pth](https://drive.google.com/drive/folders/1K2dcWxaqOLiQ3PoqRdokrgWsGIf3yBA_) in it.

2. A pre-trained EgoFlow [model](https://drive.google.com/file/d/1SdGQZddJ34A7Cd39wk6GX50QVWg_V19p/view?usp=share_link) for testing

### Dataset
1. Download [Ego4D dataset](https://ego4d-data.org/docs/) following the official guidance.

2. Run all "\*_odd.py" and "\*_even.py" files to generate the optical flows. Please check the roots of datasets in these python files.

### Train
```
python run.py --model GazeLSTM --exp_path output_train --num_workers 16 --batch_size 64 --gamma 0.5
```

### Test
```
python run.py --eval --checkpoint checkpoint_EgoFlow.pth --model GazeLSTM --exp_path output_test --num_workers 16 --batch_size 128
```
