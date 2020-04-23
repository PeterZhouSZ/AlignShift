import numpy as np
from scipy import interpolate
import torch

def recall(pred, target):

    pred_label = pred.detach().clone()
    pred_label[pred_label>=0] = 1
    pred_label[pred_label<0] = 0

    pred_label = pred_label.flatten()
    correct = pred_label.eq(target) * target

    return correct.sum().to(torch.float)/target.sum()


def eval_DL_detection(predictions, logger, is_validation):
    fns = sorted(predictions.keys())
    all_boxes = [predictions[fn]['result'].bbox.numpy() for fn in fns]
    all_scores = [predictions[fn]['result'].get_field('scores').numpy() for fn in fns]
    all_boxes = [np.hstack((b, s.reshape((-1, 1)))) for (b, s) in zip(all_boxes, all_scores)]
    all_gts = [predictions[fn]['target'].bbox.cpu().numpy() for fn in fns]

    # detection

    det_res = sens_at_FP(all_boxes, all_gts, cfg.TEST.VAL_FROC_FP, cfg.TEST.IOU_TH)  # cls 0 is background
    logger.info(', '.join(['%.4f'%v for v in det_res]))
    logger.info('mean of %s: %.4f', str(cfg.TEST.VAL_FROC_FP[:4]), np.mean(det_res[:4]))



def sens_at_FP(boxes_all, gts_all, avgFP, iou_th):
    """compute the sensitivity at avgFP (average FP per image)"""
    # boxes_all = [list(b) for b in boxes_all_r]
    sens, fp_per_img = FROC(boxes_all, gts_all, iou_th)
    avgFP_in = [a for a in avgFP if a <= fp_per_img[-1]]
    avgFP_out = [a for a in avgFP if a > fp_per_img[-1]]
    f = interpolate.interp1d(fp_per_img, sens)
    res = np.hstack([f(np.array(avgFP_in)), np.ones((len(avgFP_out, )))*sens[-1]])
    return res


def FROC(boxes_all, gts_all, iou_th):
    """Compute the Free ROC curve, for single class only"""
    nImg = len(boxes_all)
    img_idxs = np.hstack([[i]*len(boxes_all[i]) for i in range(nImg)]).astype(int)
    boxes_cat = np.vstack(boxes_all)
    scores = boxes_cat[:, -1]
    ord = np.argsort(scores)[::-1]
    boxes_cat = boxes_cat[ord, :4]
    img_idxs = img_idxs[ord]

    hits = [np.zeros((len(gts),), dtype=bool) for gts in gts_all]
    nHits = 0
    nMiss = 0
    tps = []
    fps = []
    for i in range(len(boxes_cat)):
        overlaps = IOU(boxes_cat[i, :], gts_all[img_idxs[i]])
        if len(overlaps) == 0 or overlaps.max() < iou_th:
            nMiss += 1
        else:
            for j in range(len(overlaps)):
                if overlaps[j] >= iou_th and not hits[img_idxs[i]][j]:
                    hits[img_idxs[i]][j] = True
                    nHits += 1

        tps.append(nHits)
        fps.append(nMiss)

    nGt = len(np.vstack(gts_all))
    sens = np.array(tps, dtype=float) / nGt
    fp_per_img = np.array(fps, dtype=float) / nImg

    return sens, fp_per_img


def IOU(box1, gts):
    """compute overlaps over intersection"""
    ixmin = np.maximum(gts[:, 0], box1[0])
    iymin = np.maximum(gts[:, 1], box1[1])
    ixmax = np.minimum(gts[:, 2], box1[2])
    iymax = np.minimum(gts[:, 3], box1[3])
    iw = np.maximum(ixmax - ixmin + 1., 0.)
    ih = np.maximum(iymax - iymin + 1., 0.)
    inters = iw * ih

    # union
    uni = ((box1[2] - box1[0] + 1.) * (box1[3] - box1[1] + 1.) +
           (gts[:, 2] - gts[:, 0] + 1.) *
           (gts[:, 3] - gts[:, 1] + 1.) - inters)

    overlaps = inters / uni
    # ovmax = np.max(overlaps)
    # jmax = np.argmax(overlaps)
    return overlaps
