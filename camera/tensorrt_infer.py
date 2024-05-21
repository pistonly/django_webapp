# Ultralytics YOLO 🚀, AGPL-3.0 license

import argparse

import cv2
import numpy as np
import onnxruntime as ort
import tensorrt as trt
import json
import torch

from ultralytics.utils import ASSETS, yaml_load
from ultralytics.utils.checks import check_requirements, check_yaml
import ast
import time
from collections import namedtuple, OrderedDict


class YOLOv8:
    """YOLOv8 object detection model class for handling inference and visualization."""

    def __init__(self, engine_path, confidence_thres, iou_thres):
        """
        Initializes an instance of the YOLOv8 class.

        Args:
            onnx_model: Path to the ONNX model.
            input_image: Path to the input image.
            confidence_thres: Confidence threshold for filtering detections.
            iou_thres: IoU (Intersection over Union) threshold for non-maximum suppression.
        """
        self.confidence_thres = confidence_thres
        self.iou_thres = iou_thres

        # tensorrt init
        Binding = namedtuple("Binding", ("name", "dtype", "shape", "data", "ptr"))
        logger = trt.Logger(trt.Logger.INFO)

        # Read file
        with open(engine_path, "rb") as f, trt.Runtime(logger) as runtime:
            try:
                meta_len = int.from_bytes(f.read(4), byteorder="little")  # read metadata length
                metadata = json.loads(f.read(meta_len).decode("utf-8"))  # read metadata
            except UnicodeDecodeError:
                f.seek(0)  # engine file may lack embedded Ultralytics metadata
            model = runtime.deserialize_cuda_engine(f.read())  # read engine

        # Model context
        try:
            self.context = model.create_execution_context()
        except Exception as e:  # model is None
            print(f"ERROR: TensorRT model exported with a different version than {trt.__version__}\n")
            raise e

        self.bindings = OrderedDict()
        self.output_names = []
        self.fp16 = False  # default updated below
        self.dynamic = False
        is_trt10 = not hasattr(model, "num_bindings")
        num = range(model.num_io_tensors) if is_trt10 else range(model.num_bindings)

        if not is_trt10:
            raise RuntimeError("Error: trt should be trt10")

        self.device = torch.device("cuda:0")
        for i in num:
            name = model.get_tensor_name(i)
            dtype = trt.nptype(model.get_tensor_dtype(name))
            is_input = model.get_tensor_mode(name) == trt.TensorIOMode.INPUT
            if is_input:
                if -1 in tuple(model.get_tensor_shape(name)):
                    self.dynamic = True
                    self.context.set_input_shape(name, tuple(model.get_tensor_profile_shape(name, 0)[1]))
                    if dtype == np.float16:
                        self.fp16 = True
            else:
                self.output_names.append(name)
            shape = tuple(self.context.get_tensor_shape(name))
            im = torch.from_numpy(np.empty(shape, dtype=dtype)).to(self.device)
            self.bindings[name] = Binding(name, dtype, shape, im, int(im.data_ptr()))
        self.binding_addrs = OrderedDict((n, d.ptr) for n, d in self.bindings.items())
        n, c, h, w = self.bindings["images"].shape
        self.batch_size = n # if dynamic, this is instead max batch size
        self.input_height = h
        self.input_width = w

        # Load the class names from the onnx
        if metadata:
            self.classes = {int(k): v for k, v in metadata['names'].items()}
        else:
            self.classes = yaml_load(check_yaml("coco8.yaml"))["names"]

        # Generate a color palette for the classes
        self.color_palette = np.random.uniform(0, 255, size=(len(self.classes), 3))

    def draw_detections(self, img, box, score, class_id):
        """
        Draws bounding boxes and labels on the input image based on the detected objects.

        Args:
            img: The input image to draw detections on.
            box: Detected bounding box.
            score: Corresponding detection score.
            class_id: Class ID for the detected object.

        Returns:
            None
        """

        # Extract the coordinates of the bounding box
        x1, y1, w, h = box

        # Retrieve the color for the class ID
        color = self.color_palette[class_id]

        # Draw the bounding box on the image
        cv2.rectangle(img, (int(x1), int(y1)), (int(x1 + w), int(y1 + h)), color, 2)

        # Create the label text with class name and score
        label = f"{self.classes[class_id]}: {score:.2f}"

        # Calculate the dimensions of the label text
        (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

        # Calculate the position of the label text
        label_x = x1
        label_y = y1 - 10 if y1 - 10 > label_height else y1 + 10

        # Draw a filled rectangle as the background for the label text
        cv2.rectangle(
            img, (label_x, label_y - label_height), (label_x + label_width, label_y + label_height), color, cv2.FILLED
        )

        # Draw the label text on the image
        cv2.putText(img, label, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    def preprocess(self, input_img):
        """
        Preprocesses the input image before performing inference.

        Returns:
            image_data: Preprocessed image data ready for inference.
        """
        # Read the input image using OpenCV
        if isinstance(input_img, str):
            self.img = cv2.imread(input_img)
        else:
            # io.BytesIO
            image_data = np.frombuffer(input_img.getvalue(), dtype=np.uint8)
            self.img = cv2.imdecode(image_data, cv2.IMREAD_GRAYSCALE)

        # Get the height and width of the input image
        self.img_height, self.img_width = self.img.shape[:2]

        # Convert the image color space from BGR to RGB
        img = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)

        # Resize the image to match the input shape
        img = cv2.resize(img, (self.input_width, self.input_height))

        # Normalize the image data by dividing it by 255.0
        image_data = np.array(img) / 255.0

        # Transpose the image to have the channel dimension as the first dimension
        image_data = np.transpose(image_data, (2, 0, 1))  # Channel first

        # Expand the dimensions of the image data to match the expected input shape
        image_data = np.expand_dims(image_data, axis=0).astype(np.float32)
        # NOTE: important
        image_data = np.ascontiguousarray(image_data)

        # Return the preprocessed image data
        return image_data

    def forward(self, im):
        im = torch.tensor(im).to(self.device)
        if self.dynamic or im.shape != self.bindings["images"].shape:
            self.context.set_input_shape("images", im.shape)
            self.bindings["images"] = self.bindings["images"]._replace(shape=im.shape)
            for name in self.output_names:
                self.bindings[name].data.resize_(tuple(self.context.get_tensor_shape(name)))

        s = self.bindings["images"].shape
        assert im.shape == s, f"input size {im.shape} {'>' if self.dynamic else 'not equal to'} max model size {s}"
        self.binding_addrs["images"] = int(im.data_ptr())
        self.context.execute_v2(list(self.binding_addrs.values()))
        y = [self.bindings[x].data for x in sorted(self.output_names)]
        return [y_i.cpu().numpy() for y_i in y]


    def postprocess(self, input_image, output):
        """
        Performs post-processing on the model's output to extract bounding boxes, scores, and class IDs.

        Args:
            input_image (numpy.ndarray): The input image.
            output (numpy.ndarray): The output of the model.

        Returns:
            numpy.ndarray: The input image with detections drawn on it.
        """

        # Transpose and squeeze the output to match the expected shape
        outputs = np.transpose(np.squeeze(output[0]))

        # Get the number of rows in the outputs array
        rows = outputs.shape[0]

        # Lists to store the bounding boxes, scores, and class IDs of the detections
        boxes = []
        scores = []
        class_ids = []

        # Calculate the scaling factors for the bounding box coordinates
        x_factor = self.img_width / self.input_width
        y_factor = self.img_height / self.input_height

        # Iterate over each row in the outputs array
        for i in range(rows):
            # Extract the class scores from the current row
            classes_scores = outputs[i][4:]

            # Find the maximum score among the class scores
            max_score = np.amax(classes_scores)

            # If the maximum score is above the confidence threshold
            if max_score >= self.confidence_thres:
                # Get the class ID with the highest score
                class_id = np.argmax(classes_scores)

                # Extract the bounding box coordinates from the current row
                x, y, w, h = outputs[i][0], outputs[i][1], outputs[i][2], outputs[i][3]

                # Calculate the scaled coordinates of the bounding box
                left = int((x - w / 2) * x_factor)
                top = int((y - h / 2) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)

                # Add the class ID, score, and box coordinates to the respective lists
                class_ids.append(class_id)
                scores.append(max_score)
                boxes.append([left, top, width, height])

        # Apply non-maximum suppression to filter out overlapping bounding boxes
        indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_thres, self.iou_thres)

        # Iterate over the selected indices after non-maximum suppression
        pred_class_ids = []
        for i in indices:
            # Get the box, score, and class ID corresponding to the index
            box = boxes[i]
            score = scores[i]
            class_id = class_ids[i]
            pred_class_ids.append(class_id)

            # Draw the detection on the input image
            self.draw_detections(input_image, box, score, class_id)

        # Return the modified input image
        return input_image, pred_class_ids

    def process_one_image(self, input_path):
        """
        Performs inference using an ONNX model and returns the output image with drawn detections.

        Returns:
            output_img: The output image with drawn detections.
        """
        # Preprocess the image data
        img_data = self.preprocess(input_path)

        # Run inference using the preprocessed image data
        outputs = self.forward(img_data)

        # Perform post-processing on the outputs to obtain output image.
        result = self.postprocess(self.img, outputs)  # output image
        return result


if __name__ == "__main__":
    # Create an argument parser to handle command-line arguments
    default_engine = "../../yolo_models/hsh_18_model_640.engine"
    default_img = "./data/test1-0_20240514-152234-0__1.jpg"
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=default_engine, help="Input your engine model.")
    parser.add_argument("--img", type=str, default=default_img, help="Path to input image.")
    parser.add_argument("--conf-thres", type=float, default=0.01, help="Confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.5, help="NMS IoU threshold")
    args = parser.parse_args()

    # Create an instance of the YOLOv8 class with the specified arguments
    detection = YOLOv8(args.model, args.conf_thres, args.iou_thres)

    # Perform object detection and obtain the output image
    output_image = detection.process_one_image(args.img)

    # Display the output image in a window
    cv2.namedWindow("Output", cv2.WINDOW_NORMAL)
    cv2.imshow("Output", output_image)

    # Wait for a key press to exit
    cv2.waitKey(0)
