"""针对方向错误、黑色有效像素和退化输入的行为测试。"""
import unittest
import cv2
import numpy as np
from src.stitching import stitch_pair, warp_layers, blend_layers, extract_features, StitchingError


class StitchingTests(unittest.TestCase):
    def test_known_translation(self):
        rng=np.random.default_rng(12)
        full=rng.integers(0,256,(320,700,3),dtype=np.uint8)
        full=cv2.GaussianBlur(full,(3,3),0)
        a,b=full[:,:460],full[:,240:]
        fit=stitch_pair(a,b)
        mapped=cv2.perspectiveTransform(np.float32([[[100,100]]]),fit['H'])[0,0]
        np.testing.assert_allclose(mapped,[340,100],atol=1.0)
        self.assertGreater(fit['metrics']['inlier_ratio'],.9)

    def test_black_pixels_are_valid(self):
        black=np.zeros((40,40,3),np.uint8)
        white=np.full((40,40,3),200,np.uint8)
        layers,masks,_=warp_layers([black,white],[np.eye(3),np.eye(3)])
        blended=blend_layers(layers,masks)
        self.assertTrue(masks[0].all())
        self.assertTrue(99 <= blended[20,20,0] <= 100)

    def test_textureless_is_rejected(self):
        with self.assertRaises(StitchingError):
            extract_features(np.zeros((200,200,3),np.uint8))

    def test_unbounded_canvas_is_rejected(self):
        H=np.array([[1,0,0],[0,1,0],[-.02,0,1.]])
        with self.assertRaises(StitchingError):
            warp_layers([np.zeros((100,100,3),np.uint8)],[H])

if __name__=='__main__':
    unittest.main()
