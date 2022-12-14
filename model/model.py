import torch, os, math, logging
import torch.nn as nn
import torch.optim
import torch.utils.data
from torch.nn.init import normal, constant
from model.resnet import resnet18
from torchvision.transforms import Resize 
import time


logger = logging.getLogger(__name__)


class BaselineLSTM(nn.Module):
    def __init__(self, args):
        super(BaselineLSTM, self).__init__()
        self.args = args
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame
        self.base_model = resnet18(pretrained=False)
        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)
        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim, bidirectional=True, num_layers=2, batch_first=True)
        self.last_layer1 = nn.Linear(2*self.img_feature_dim, 128)
        self.last_layer2 = nn.Linear(128, 2)

        for param in self.parameters():
            param.requires_grad = True
        
        self._init_parameters()
        
        self.load_checkpoint()

    def forward(self, input):
        N, D, C, H, W = input.shape
        base_out = self.base_model(input.view(N*D, C, H, W))
        base_out = base_out.view(N, D, self.img_feature_dim)
        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:,3,:]
        output = self.last_layer1(lstm_out)
        output = self.last_layer2(output)
        return output

    def load_checkpoint(self):
        if self.args.checkpoint is not None:
            if os.path.exists(self.args.checkpoint):
                logger.info(f'loading checkpoint {self.args.checkpoint}')
                state = torch.load(self.args.checkpoint, map_location=f'cuda:{self.args.rank}')
                if 'module' in list(state["state_dict"].keys())[0]:
                    state_dict = { k[7:]: v for k, v in state["state_dict"].items() }
                else:
                    state_dict = state["state_dict"]
                self.load_state_dict(state_dict)
        
    def _init_parameters(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)


class GazeLSTM(nn.Module):
    def __init__(self, args):
        super(GazeLSTM, self).__init__()
        self.args = args
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame
        self.base_model = resnet18(pretrained=True)
        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)
        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim,bidirectional=True,num_layers=2,batch_first=True)
        # The linear layer that maps the LSTM with the 2 outputs
        # ---------------------------------------------------------------------
        # ??????????????????
        # ????????????????????????
            # 1??????????????????concatenate
            # 2??????????????????add???????????????????????????????????????????????????????????????????????????
            # 3?????????FC???concatenate??????TTM???
            # ??????1???2
        # self.last_layer1 = nn.Linear(2 * self.img_feature_dim, 128)
        # self.last_layer1_of_1 = nn.Linear(2 * self.img_feature_dim, 128)
        # self.last_layer1_of_2 = nn.Linear(2 * self.img_feature_dim, 128)
        # self.last_layer2 = nn.Linear(128, 2)  # ??????2
        # # self.last_layer2 = nn.Linear(384, 2)  # ??????1
            # ??????3
        self.last_layer1 = nn.Linear(6 * self.img_feature_dim, 128)
        self.last_layer2 = nn.Linear(128, 2)
        # Optical Flow??????
        self.base_model_of = resnet18(pretrained=True)
        self.base_model_of.fc2 = nn.Linear(1000, self.img_feature_dim)
        self.lstm_of = nn.LSTM(self.img_feature_dim, self.img_feature_dim,bidirectional=True,num_layers=2,batch_first=True)
        # ---------------------------------------------------------------------
        self.load_checkpoint()

    def forward(self, input):
        # start = time.time()
        # print(input.shape)  torch.Size([2, 13, 3, 224, 224])
        # RGB??????
        rgb = input[:, :7, :, :, :]
        # print(rgb.shape)  torch.Size([2, 7, 3, 224, 224])
        base_out = self.base_model(rgb.contiguous().view((-1, 3) + rgb.size()[-2:]))
        # print("--------------------------------------------------------------")
        # print(base_out.shape)  torch.Size([1792, 256])
        base_out = base_out.view(rgb.size(0),7,self.img_feature_dim)
        # print(base_out.shape)  torch.Size([256, 7, 256])
        lstm_out, _ = self.lstm(base_out)
        # print(lstm_out.shape)  torch.Size([256, 7, 512])
        # print('RGB Path: %.3f s' % (time.time() - start))  0.233 s
        
        # Optical Flow??????
        # start = time.time()
        of = input[:, 7:, :, :, :]
        # print(of)
        base_out = self.base_model_of(of.contiguous().view((-1, 3) + of.size()[-2:]))
        # print("--------------------------------------------------------------")
        # print(base_out.shape)
        base_out = base_out.view(of.size(0),6,self.img_feature_dim)
        # print(base_out.shape)
        lstm_out_of, _ = self.lstm_of(base_out)
        # print(lstm_out_of.shape)  torch.Size([2, 6, 512]
        # print('Optical-Flow Path: %.3f s' % (time.time() - start))  0.024 s
        
        # start = time.time()
        lstm_out = lstm_out[:,3,:]
        lstm_out_of_1 = lstm_out_of[:, 2, :]
        lstm_out_of_2 = lstm_out_of[:, 3, :]
        # print("---------------------------FC---------------------------------")
        # print(lstm_out.shape)  torch.Size([256, 512])
            # ??????1???2
        # output = self.last_layer1(lstm_out)
        # output_of_1 = self.last_layer1_of_1(lstm_out_of_1)
        # output_of_2 = self.last_layer1_of_2(lstm_out_of_2)
        # # output = torch.cat([output, output_of_1, output_of_2], -1)  # ??????1
        # output = torch.add(output, output_of_1)  # ??????2
        # output = torch.add(output, output_of_2)  # ??????2
        # output = self.last_layer2(output).view(-1,2)
            # ??????3
        output = torch.cat([lstm_out, lstm_out_of_1], -1)
        output = torch.cat([output, lstm_out_of_2], -1)
        output = self.last_layer1(output)
        output = self.last_layer2(output).view(-1,2)
        # print(output.shape)  torch.Size([256, 2])
        # print('FC: %.3f s' % (time.time() - start))  0.000 s
        return output
    
    # ???????????????????????????Optical Flow????????????????????????
    def load_checkpoint(self):
        if self.args.checkpoint is not None:
            if os.path.exists(self.args.checkpoint):
                logger.info(f'loading checkpoint {self.args.checkpoint}')
                map_loc = f'cuda:{self.args.rank}' if torch.cuda.is_available() else 'cpu'
                state = torch.load(self.args.checkpoint, map_location=map_loc)
                model_dict = self.state_dict()  # ????????????
                if 'module' in list(state["state_dict"].keys())[0]:
                    print(1)
                    state_dict = { k[7:]: v for k, v in state["state_dict"].items() }
                else:
                    print(2)
                    # state_dict = state["state_dict"]
                    state_dict = {k:v for k,v in state["state_dict"].items() if k in 
                                  model_dict.keys()}
                self.load_state_dict(state_dict, strict=self.args.eval)
                    # ??????1???2
                # # ??????????????????????????????????????????????????????????????????2??????????????????????????????
                # # state_dict.pop('last_layer2.weight')
                # # state_dict.pop('last_layer2.bias')
                # # print(state_dict.keys())
                # model_dict.update(state_dict)
                # self.load_state_dict(model_dict, strict=self.args.eval)
                # # ??????base_model_of???lstm_of???last_layer1_of_1???last_layer1_of_2
                #     # ?????????????????????????????????????????????
                # # self.base_model_of.load_state_dict(self.base_model.state_dict())
                # # self.lstm_of.load_state_dict(self.lstm.state_dict())
                # # self.last_layer1_of_1.load_state_dict(self.last_layer1.state_dict())
                # # self.last_layer1_of_2.load_state_dict(self.last_layer1.state_dict())
                    # ??????3????????????2??????????????????????????????
                # state_dict.pop('last_layer1.weight')
                # state_dict.pop('last_layer1.bias')
                # model_dict.update(state_dict)
                # self.load_state_dict(model_dict, strict=self.args.eval)
                    # ??????3??????gaze360???????????????
                # self.base_model_of.load_state_dict(self.base_model.state_dict())
                # self.lstm_of.load_state_dict(self.lstm.state_dict())
                # model_dict.update(state_dict)
                # self.load_state_dict(model_dict, strict=self.args.eval)
                


if __name__ == '__main__':
    input_test = torch.FloatTensor(4,21,224,224)
    model_test = BaselineLSTM()
    out = model_test.forward(input_test)
