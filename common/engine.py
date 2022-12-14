import os, logging
import time
import torch
import torch.optim
import torch.utils.data
from common.utils import AverageMeter
from common.distributed import is_master


logger = logging.getLogger(__name__)


def train(train_loader, model, criterion, optimizer, epoch):
    logger.info('training')
    batch_time = AverageMeter()
    data_time = AverageMeter()
    avg_loss = AverageMeter()

    model.train()
    # for param in model.model_FlowFormer.parameters():
    #     print(param.requires_grad)  一大堆False

    end = time.time()

    for i,  (source_frame, target) in enumerate(train_loader):

        # measure data loading time
        data_time.update(time.time() - end)
        source_frame = source_frame.cuda()
        target = target.cuda()

        # compute output
        # temp = time.time()
        output = model(source_frame)
        # print('Model Forward: %.3f s' % (time.time() - temp))  0.028 s

        # from common.render import visualize_gaze
        # for i in range(32):
        #     visualize_gaze(source_frame, output[0], index=i, title=str(i))

        # temp = time.time()
        target = target.squeeze(1)
        loss = criterion(output, target)
        # print('Calculating Loss: %.3f s' % (time.time() - temp))  0.000 s

        # temp = time.time()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        # print('Optimization: %.3f s' % (time.time() - temp))  0.819 s
        avg_loss.update(loss.item())

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()
        
        if i % 100 == 0:
            logger.info('Epoch: [{0}][{1}/{2}]\t'
                        'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                        'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'
                        'Loss {loss.val:.4f} ({loss.avg:.4f})\t'.format(
                        epoch, i, len(train_loader), batch_time=batch_time,
                        data_time=data_time, loss=avg_loss))
            
    return avg_loss


def validate(val_loader, model, postprocess, mode='val'):
    logger.info('evaluating')
    batch_time = AverageMeter()
    model.eval()
    end = time.time()

    for i, (source_frame, target) in enumerate(val_loader):

        source_frame = source_frame.cuda()
        # print(source_frame.shape)  torch.Size([256, 7, 3, 224, 224])

        with torch.no_grad():
            output = model(source_frame)
            # print(output.shape)  torch.Size([256, 2])
            postprocess.update(output.detach().cpu(), target)

            batch_time.update(time.time() - end)
            end = time.time()

        if i % 100 == 0:
            logger.info('Processed: [{0}/{1}]\t'
                        'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'.format(
                        i, len(val_loader), batch_time=batch_time))
    postprocess.save()

    if mode == 'val':
        mAP = None
        if is_master():
            mAP = postprocess.get_mAP()
        return mAP

    if mode == 'test':
        print('generate pred.csv')
