anchor_scales = [4, 6, 8, 12, 24, 48]#, 64
# fp16 = dict(loss_scale=96.)

dataset_transform = dict(
    IMG_DO_CLIP = False,
    # PIXEL_MEAN = 0.5,
    WINDOWING = [-1024, 2050],
    DATA_AUG_POSITION = False,
    NORM_SPACING = 0.,
    SLICE_INTV = 2.0,
    NUM_SLICES = 7,
    GROUNP_ZSAPACING = False,
)
input_channel = dataset_transform['NUM_SLICES']
feature_channel = 512
# model settings
weights2d_path = None,
model = dict(
    type='MaskRCNN',
    pretrained= False,
    backbone=dict(
        type='DenseNetCustomTrunc',
        out_dim=512,
        fpn_finest_layer=2,),
    rpn_head=dict(
        type='RPNHead',
        in_channels=feature_channel,
        feat_channels=feature_channel,###原版这俩好像没有conv
        anchor_scales=anchor_scales,
        anchor_ratios=[0.5, 1., 2.0],
        anchor_base_sizes=[4],
        anchor_strides=[4],
        target_means=[.0, .0, .0, .0],
        target_stds=[1., 1., 1., 1.],
        loss_cls=dict(
            type='CrossEntropyLoss', use_sigmoid=True, loss_weight=1.0),
        loss_bbox=dict(type='SmoothL1Loss', beta=1.0 / 9.0, loss_weight=1.0)),
    bbox_roi_extractor=dict(
        type='SingleRoIExtractor',
        roi_layer=dict(type='RoIAlign', out_size=7, sample_num=2),
        out_channels=feature_channel,
        featmap_strides=[4]),
    bbox_head=dict(
        type='SharedFCBBoxHead',
        num_fcs=2,
        in_channels=feature_channel,
        fc_out_channels=feature_channel * 4,
        roi_feat_size=7,
        num_classes=2,
        num_shared_convs=0,
        target_means=[0., 0., 0., 0.],
        target_stds=[0.1, 0.1, 0.2, 0.2],
        # target_stds=[1., 1., 1., 1.],
        reg_class_agnostic=False,
        loss_cls=dict(
            type='CrossEntropyLoss', use_sigmoid=False, loss_weight=1.0),
        loss_bbox=dict(type='SmoothL1Loss', beta=1.0, loss_weight=1.0)),
    mask_roi_extractor=dict(
        type='SingleRoIExtractor',
        roi_layer=dict(type='RoIAlign', out_size=14, sample_num=2),
        finest_scale=196, #按照面积是这个的倍数， 到该层去取feature
        out_channels=feature_channel,
        featmap_strides=[4]),
    mask_head=dict(
        type='FCNMaskHead',
        num_convs=4,
        in_channels=feature_channel,
        conv_out_channels=feature_channel // 2,
        num_classes=2,
        loss_mask=dict(
            type='DiceLoss', use_mask=True, loss_weight=1.0)))##DiceLoss， CrossEntropyLoss
# model training and testing settings
train_cfg = dict(
    rpn=dict(
        assigner=dict(
            type='MaxIoUAssigner',
            pos_iou_thr=0.7,
            neg_iou_thr=0.3,
            min_pos_iou=0.3,
            ignore_iof_thr=-1),
        sampler=dict(
            type='RandomSampler',
            num=32,
            pos_fraction=0.5,
            neg_pos_ub=-1,
            add_gt_as_proposals=False),
        allowed_border=0,
        pos_weight=-1,
        debug=False),
    rpn_proposal=dict(
        nms_across_levels=False,
        nms_pre=12000,
        nms_post=2000,
        max_num=2000,
        nms_thr=0.7,# 越大 抑制越少
        min_bbox_size=0),
    rcnn=dict(
        assigner=dict(
            type='MaxIoUAssigner',
            pos_iou_thr=0.5,
            neg_iou_thr=0.5,
            min_pos_iou=0.5,
            ignore_iof_thr=-1),
        sampler=dict(
            type='RandomSampler',
            num=64,
            pos_fraction=0.25,
            neg_pos_ub=-1,
            add_gt_as_proposals=True),
        mask_size=28,
        pos_weight=-1,
        debug=False))
test_cfg = dict(
    avgFP=[0.5, 1, 2, 4, 8, 16],
    iou_th_astrue=0.5,
    rpn=dict(
        nms_across_levels=False,
        nms_pre=6000,
        nms_post=300,
        max_num=300,
        nms_thr=0.7,
        min_bbox_size=0),
    rcnn=dict(
        score_thr=0.005,
        nms=dict(type='nms', iou_thr=0.5),
        max_per_img=50,
        mask_thr_binary=0.5))
# dataset settings
dataset_type = 'DeepLesionDataset_25d'

data_root = '/mnt/data/DeepLesion/'
img_norm_cfg = dict(
    mean=[0.] * input_channel, std=[1.] * input_channel, to_rgb=False)
pre_pipeline=[
    dict(
        type='Albu',
        transforms=[dict(
                    type='ShiftScaleRotate',
                    shift_limit=0.04,
                    scale_limit=0.2,
                    rotate_limit=15,
                    interpolation=2,## cv::BORDER_REFLECT
                    p=0.8),],#dict(type='Rotate', limit=15, p=0.5)
        bbox_params=dict(
            type='BboxParams',
            format='pascal_voc',
            label_fields=['gt_labels'],
            min_visibility=0.0),
        keymap={
            'img': 'image',
            'gt_masks': 'masks',
            'gt_bboxes': 'bboxes'
        },
        update_pad_shape=False,
        skip_img_without_anno=False),
    dict(type='Resize', img_scale=(512, 512), keep_ratio=True),
    dict(type='RandomFlip', flip_ratio=0.5),
    dict(type='Normalize', **img_norm_cfg),
    dict(type='Pad', size_divisor=32),    
]
pre_pipeline_test=[
    dict(type='Resize', img_scale=(512, 512), keep_ratio=True),
    dict(type='RandomFlip', flip_ratio=0),
    dict(type='Normalize', **img_norm_cfg),
    dict(type='Pad', size_divisor=32),    
]
train_pipeline = [
    dict(type='DefaultFormatBundle'),
    dict(type='Collect', keys=['img', 'gt_bboxes', 'gt_labels', 'gt_masks', 'z_spacing']),#, 'flage'#, 'img_info'#, 'z_spacing'
]

test_pipeline = [
    dict(type='ImageToTensor', keys=['img']),
    dict(type='Collect', keys=['img', 'gt_bboxes']),
]
data = dict(
    # train_dataloader=dict(
    #         imgs_per_gpu=4,
    #         workers_per_gpu=4,),
    # val_dataloader=dict(
    #         imgs_per_gpu=1,
    #         workers_per_gpu=4,),
    imgs_per_gpu=16,
    workers_per_gpu=4,
    train=dict(
        type=dataset_type,
        ann_file=data_root + 'train_ann.pkl',
        image_path=data_root + 'Images_png/',
        pipeline=train_pipeline,
        pre_pipeline = pre_pipeline,
        dicm2png_cfg=dataset_transform),
        with_mask=True,
        with_label=True,
    test=dict(
        type=dataset_type,
        ann_file=data_root + 'val_ann.pkl',
        image_path=data_root + 'Images_png/',
        pipeline=train_pipeline,
        pre_pipeline = pre_pipeline_test,
        dicm2png_cfg=dataset_transform),
    val=dict(
        type=dataset_type,
        ann_file=data_root + 'test_ann.pkl',
        image_path=data_root + 'Images_png/',
        pipeline=train_pipeline,
        pre_pipeline = pre_pipeline_test,
        dicm2png_cfg=dataset_transform))
# optimizer
optimizer = dict(type='SGD', lr=0.02, momentum=0.9, weight_decay=0.0001)#momentum=0.9,
optimizer_config = dict(grad_clip=dict(max_norm=35, norm_type=2))#, step_inteval=2
# learning policy
lr_config = dict(
    policy='step',
    warmup='linear',
    warmup_iters=500,
    warmup_ratio=1/100,
    step=[9, 16])#10,13
checkpoint_config = dict(interval=1)
# yapf:disable
log_config = dict(
    interval=100,
    hooks=[
        dict(type='TextLoggerHook'),
        dict(type='TensorboardLoggerHook')
    ])
# yapf:enable
evaluation = dict(interval=1)
# runtime settings
total_epochs = 20#16
dist_params = dict(backend='nccl')
log_level = 'INFO'
work_dir = f'./work_dirs/densenet_25d_r3'
load_from = None
resume_from = None
workflow = [('train', 1)]#, ('val',1)
GPU = '0,1,2,3'
description='25d 7cts'

#TODO:adam, dice # 9 slice(太占内存), TSMinplace(还是可以对比试验一下，
#按distribute的方式应该是不存在的) 优化 fp16看看
#只取中间那一张再看看，理论上应该这么做, 3D的pooling应该更好，后面试试
#试试rangdom shift scale
#achive:
#adam x
#feature channel 256 差别不大 有对比过
#看看shift 到底是哪个波动, 刚开始的时候inplace后结果不一样，但是后来又不一样了。总的来说没啥区别，现在看来的话
#有条件可以把mask head 调少下，后续按照自己的感觉来搞一个prune版的，应该要不了这么大权重
#可以直接读取不align的权重来验证2mmspacing以下的对不对哦, 最开始只tsm的权重;确实有问题，我改了spacing
#后面还要看看是不是我的anchor不够大， 分lesion_size看看指标，理论上也没有太大问题，应为我和其他是一样的。
#新的align加shift的channel 应该有效果。
#add checkpoint  改了forward的逻辑， 需要检查
#7ct 要算3days 暂时放弃
#1、try soft_nms