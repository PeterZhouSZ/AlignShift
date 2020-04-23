import torch.nn as nn

from mmdet.core import bbox2result
from .. import builder
from ..registry import DETECTORS
from .base import BaseDetector
import numpy as np

@DETECTORS.register_module
class SingleStageDetector(BaseDetector):
    """Base class for single-stage detectors.

    Single-stage detectors directly and densely predict bounding boxes on the
    output features of the backbone+neck.
    """

    def __init__(self,
                 backbone,
                 neck=None,
                 bbox_head=None,
                 mask_head=None,
                 train_cfg=None,
                 test_cfg=None,
                 pretrained=None):
        super(SingleStageDetector, self).__init__()
        self.backbone = builder.build_backbone(backbone)
        if neck is not None:
            self.neck = builder.build_neck(neck)
        self.bbox_head = builder.build_head(bbox_head)
        if mask_head is not None:
            self.mask_head = builder.build_head(mask_head)
        self.train_cfg = train_cfg
        self.test_cfg = test_cfg
        self.init_weights(pretrained=pretrained)

    def init_weights(self, pretrained=None):
        super(SingleStageDetector, self).init_weights(pretrained)
        self.backbone.init_weights(pretrained=pretrained)
        if self.with_neck:
            if isinstance(self.neck, nn.Sequential):
                for m in self.neck:
                    m.init_weights()
            else:
                self.neck.init_weights()
        self.bbox_head.init_weights()

    def extract_feat(self, img):
        """Directly extract features from the backbone+neck
        """
        x = self.backbone(img)
        if self.with_neck:
            x = self.neck(x)
        return x

    def forward_dummy(self, img):
        """Used for computing network flops.

        See `mmedetection/tools/get_flops.py`
        """
        x = self.extract_feat(img)
        outs = self.bbox_head(x)
        return outs

    def forward_train(self,
                      img,
                      img_metas,
                      gt_bboxes,
                      gt_labels,
                      gt_masks,
                      gt_bboxes_ignore=None):
        x = self.extract_feat(img)
        outs = self.bbox_head(x)
        mask = self.mask_head(x[0], return_feat=False)
        loss_inputs = outs + (gt_bboxes, gt_labels, img_metas, self.train_cfg)
        losses = self.bbox_head.loss(
            *loss_inputs, gt_bboxes_ignore=gt_bboxes_ignore)
        print(gt_masks)
        print(losses)
        loss_mask = self.mask_head.loss(mask.flatten(), gt_masks.flatten(), gt_labels)
        print(loss_mask)
        loss_all = dict(**losses, **loss_mask)
        print(loss_all)
        return loss_all

    def simple_test(self,
                      img,
                      img_meta, **kwargs):
        x = self.extract_feat(img)
        outs = self.bbox_head(x)
        bbox_inputs = outs + (img_meta, self.test_cfg)
        bbox_list = self.bbox_head.get_bboxes(*bbox_inputs, rescale=True)[0]
        bbox_results = [b.cpu().numpy() if b.shape[0] != 0 else np.array([[0, 0, 0, 0]]) for b in bbox_list]
        if kwargs.get('gt_bboxes'):
            loss_inputs = outs + (kwargs['gt_bboxes'], kwargs['gt_labels'], img_meta, self.train_cfg)
            losses = self.bbox_head.loss(*loss_inputs, gt_bboxes_ignore=None)
            return losses, bbox_results[0]
        else:
            return bbox_results[0]

    # def simple_test(self, img, img_meta, rescale=False):
    #     x = self.extract_feat(img)
    #     outs = self.bbox_head(x)
    #     bbox_inputs = outs + (img_meta, self.test_cfg, rescale)
    #     bbox_list = self.bbox_head.get_bboxes(*bbox_inputs, rescale=True)
    #     bbox_results = [
    #         bbox2result(det_bboxes, det_labels, self.bbox_head.num_classes)
    #         for det_bboxes, det_labels in bbox_list
    #     ]
    #     return bbox_results[0]

    def aug_test(self, imgs, img_metas, rescale=False):
        raise NotImplementedError
