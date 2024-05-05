var selecting_roi = false;
var rect_color = 'red';
var realWidth;
var realHeight;
var roi_xy0;
var roi_xy1;
var currentScale = 0;
var currentOffset = [0, 0];

function computeScaleOffset(rect_width, rect_height, real_width, real_height) {
    const scaleX = real_width / rect_width; // 计算宽度的缩放比例
    const scaleY = real_height / rect_height; // 计算高度的缩放比例
    const scale = Math.max(scaleX, scaleY);
    let offsetX = 0;
    let offsetY = 0;
    if (scaleX > scaleY) {
        offsetX = 0;
        offsetY = (rect_height * scale - realHeight) / 2;
    } else {
        offsetX = (rect_width * scale - realWidth) / 2;
        offsetY = 0;
    }
    return {
        'scale': scale,
        'offset': [offsetX, offsetY]
    };
}

function updateScaleOffset(_image) {
    let image = _image;
    if (!image) {
        image = document.getElementById('camera-image');
    }
    const rect = image.getBoundingClientRect();
    const scale_offset = computeScaleOffset(rect.width, rect.height, realWidth, realHeight);
    currentScale = scale_offset.scale;
    currentOffset = scale_offset.offset;
}

function getRealCoordinate(rect, e) {
    const data = computeScaleOffset(rect.width, rect.height, realWidth, realHeight);
    const scale = data.scale;
    const offsetX = data.offset[0];
    const offsetY = data.offset[1];
    const realX = (e.clientX - rect.left) * scale - offsetX; // 转换为真实尺寸上的X坐标
    const realY = (e.clientY - rect.top) * scale - offsetY; // 转换为真实尺寸上的Y坐标
    return [realX.toFixed(0), realY.toFixed(0)];
}

function realCoor2imageCoor(realX, realY, scale, offset) {
    imgX = (realX + offset[0]) / scale;
    imgY = (realY + offset[1]) / scale;
    return [imgX, imgY];
}

function setROI0(x0, y0, x1, y1) {
    ws.send(JSON.stringify({
        "set_camera": 1,
        "sn": $('#select_camera').val(),
        "params": {
            roi0: [x0, y0, x1, y1]
        }
    }));
}

function setROIDisable0(val) {
    ws.send(JSON.stringify({
        "set_camera": 1,
        "sn": $('#select_camera').val(),
        "params": {
            roi0_disabled: val
        }
    }));

}

function setROIDisable1(val) {
    ws.send(JSON.stringify({
        "set_camera": 1,
        "sn": $('#select_camera').val(),
        "params": {
            roi1_disabled: val
        }
    }));
}

function setROI1(x0, y0, x1, y1) {
    ws.send(JSON.stringify({
        "set_camera": 1,
        "sn": $('#select_camera').val(),
        "params": {
            roi1: [x0, y0, x1, y1]
        }
    }));
}
// Mouse Position and RGB Logic
document.addEventListener('DOMContentLoaded', function() {
    const image = document.getElementById('camera-image');
    const coordsDisplay = document.getElementById('coords');
    const roiCanvas = document.getElementById('roiCanvas');

    // 确保图片已加载获取其真实尺寸
    image.onload = function() {
        realWidth = this.naturalWidth;
        realHeight = this.naturalHeight;

        // get current scale, offset
        updateScaleOffset();

        // 确保canvas尺寸与图像相匹配
        if (roiCanvas.width != image.width || roiCanvas.height != image.height) {
            roiCanvas.width = image.width;
            roiCanvas.height = image.height;
        }


    };

    if ($('#camera-image').prop('complete')) {
        console.log("image load");
        $('#camera-image').trigger('load');
    }

});

document.addEventListener('DOMContentLoaded', function() {
    const image = document.getElementById('camera-image');
    const dragHandle = document.getElementById('dragHandle');
    const infoPanel = document.getElementById('infoPanel');
    const coordsDisplay = document.getElementById('coords');
    const rgbDisplay = document.getElementById('rgb');
    const roiCanvas = document.getElementById('roiCanvas');
    const ctx = roiCanvas.getContext('2d');
    let isResizing = false;
    let isDrawing = false;
    let reDrawRoi_flag0 = false;
    let reDrawRoi_flag1 = false;
    let startX, startY, startWidth, startHeight;

    // roi-0
    const check_roi_0 = $('#check-roi-0');
    const roi_x0_0 = $('#roi-x0-0');
    const roi_y0_0 = $('#roi-y0-0');
    const roi_x1_0 = $('#roi-x1-0');
    const roi_y1_0 = $('#roi-y1-0');
    const roi_btn_0 = $('#roi-button-0');

    // roi-1
    const check_roi_1 = $('#check-roi-1');
    const roi_x0_1 = $('#roi-x0-1');
    const roi_y0_1 = $('#roi-y0-1');
    const roi_x1_1 = $('#roi-x1-1');
    const roi_y1_1 = $('#roi-y1-1');
    const roi_btn_1 = $('#roi-button-1');

    function redrawROI0() {
        if (reDrawRoi_flag0 && roi_x0_0.val()) {
            const x0 = Number(roi_x0_0.val());
            const y0 = Number(roi_y0_0.val());
            const x1 = Number(roi_x1_0.val());
            const y1 = Number(roi_y1_0.val());
            let width = x1 - x0;
            let height = y1 - y0;
            if (width > 0 && height > 0) {
                const x0y0 = realCoor2imageCoor(x0, y0, currentScale, currentOffset);
                width = width / currentScale;
                height = height / currentScale;
                drawRect(x0y0[0], x0y0[1], width, height, 'red');
            }
        }
    }

    function redrawROI1() {
        if (reDrawRoi_flag1 && roi_x0_1.val()) {
            const x0 = Number(roi_x0_1.val());
            const y0 = Number(roi_y0_1.val());
            const x1 = Number(roi_x1_1.val());
            const y1 = Number(roi_y1_1.val());
            let width = x1 - x0;
            let height = y1 - y0;
            if (width > 0 && height > 0) {
                const x0y0 = realCoor2imageCoor(x0, y0, currentScale, currentOffset);
                width = width / currentScale;
                height = height / currentScale;
                drawRect(x0y0[0], x0y0[1], width, height, 'green');
            }
        }
    }

    // Resizing Logic
    dragHandle.addEventListener('mousedown', function(e) {
        isResizing = true;
        startX = e.clientX;
        startY = e.clientY;
        startWidth = parseInt(document.defaultView.getComputedStyle(image).width, 10);
        startHeight = parseInt(document.defaultView.getComputedStyle(image).height, 10);
        document.addEventListener('mousemove', doDrag, false);
        document.addEventListener('mouseup', stopDrag, false);
    });

    function doDrag(e) {
        if (isResizing) {
            image.style.width = (startWidth + e.clientX - startX) + 'px';
            image.style.height = (startHeight + e.clientY - startY) + 'px';
            roiCanvas.width = image.width;
            roiCanvas.height = image.height;
        }
    }

    function stopDrag() {
        isResizing = false;
        document.removeEventListener('mousemove', doDrag, false);
        document.removeEventListener('mouseup', stopDrag, false);
        // 确保canvas尺寸与图像相匹配
        roiCanvas.width = image.width;
        roiCanvas.height = image.height;

        // update scale offset
        updateScaleOffset(image);

        // redraw
        redrawROI0();
        redrawROI1();

    }


    // ROI Selection Logic (simplified)
    // Additional logic needed for drawing and managing ROI selection
    // 确保canvas尺寸与图像相匹配
    roiCanvas.width = document.getElementById('camera-image').width;
    roiCanvas.height = document.getElementById('camera-image').height;

    function drawRect(x, y, width, height, color) {
        console.log("color");
        console.log(color);
        ctx.beginPath();
        ctx.rect(x, y, width, height);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    roiCanvas.addEventListener('mousedown', (e) => {
        const rect = roiCanvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
        isDrawing = true;
        roi_xy0 = getRealCoordinate(rect, e);
        console.log("roi mousedown");
        console.log(roi_xy0);
    });

    roiCanvas.addEventListener('mousemove', (e) => {
        if (selecting_roi && isDrawing) {
            const rect = roiCanvas.getBoundingClientRect();
            const currentX = e.clientX - rect.left;
            const currentY = e.clientY - rect.top;
            const width = currentX - startX;
            const height = currentY - startY;

            // 清除canvas
            ctx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
            drawRect(startX, startY, width, height, rect_color);
        }
    });

    roiCanvas.addEventListener('mouseup', (e) => {
        isDrawing = false;

        const rect = roiCanvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
        // scale
        roi_xy1 = getRealCoordinate(rect, e);

        // draw all ROIs
        if (rect_color == 'red') {
            redrawROI1();
        } else {
            redrawROI0();
        }

    });

    function ROIButtonText0() {
        var button = document.getElementById("roi-button-0");
        if (button.textContent === "设置") {
            button.textContent = "确定";
            selecting_roi = true;
            rect_color = 'red';
            // free roi-0
            check_roi_1.prop('disabled', true);
            roi_x0_1.prop('disabled', true);
            roi_y0_1.prop('disabled', true);
            roi_x1_1.prop('disabled', true);
            roi_y1_1.prop('disabled', true);
            roi_btn_1.prop('disabled', true);
        } else {
            button.textContent = "设置";
            selecting_roi = false;
            roi_x0_0.val(roi_xy0[0]);
            roi_y0_0.val(roi_xy0[1]);
            roi_x1_0.val(roi_xy1[0]);
            roi_y1_0.val(roi_xy1[1]);
            check_roi_0.prop('checked', true);
            check_roi_0.trigger('change');
            // unfree roi-0
            check_roi_1.prop('disabled', false);
            roi_x0_1.prop('disabled', false);
            roi_y0_1.prop('disabled', false);
            roi_x1_1.prop('disabled', false);
            roi_y1_1.prop('disabled', false);
            roi_btn_1.prop('disabled', false);
            // set roi-0
            setROI0(roi_xy0[0], roi_xy0[1], roi_xy1[0], roi_xy1[1]);

        }
    }


    function ROIButtonText1() {
        var button = document.getElementById("roi-button-1");
        if (button.textContent === "设置") {
            button.textContent = "确定";
            selecting_roi = true;
            rect_color = 'green';
            // free roi-0
            check_roi_0.prop('disabled', true);
            roi_x0_0.prop('disabled', true);
            roi_y0_0.prop('disabled', true);
            roi_x1_0.prop('disabled', true);
            roi_y1_0.prop('disabled', true);
            roi_btn_0.prop('disabled', true);
        } else {
            button.textContent = "设置";
            selecting_roi = false;
            roi_x0_1.val(roi_xy0[0]);
            roi_y0_1.val(roi_xy0[1]);
            roi_x1_1.val(roi_xy1[0]);
            roi_y1_1.val(roi_xy1[1]);
            check_roi_1.prop('checked', true);
            check_roi_1.trigger('change');
            // unfree roi-0
            check_roi_0.prop('disabled', false);
            roi_x0_0.prop('disabled', false);
            roi_y0_0.prop('disabled', false);
            roi_x1_0.prop('disabled', false);
            roi_y1_0.prop('disabled', false);
            roi_btn_0.prop('disabled', false);

            // set roi1
            setROI1(roi_xy0[0], roi_xy0[1], roi_xy1[0], roi_xy1[1]);

        }
    }

    roi_btn_0.click(function() {
        ROIButtonText0();
    });

    roi_btn_1.click(function() {
        ROIButtonText1();
    });

    function check_roi_fun0() {
        if (this.checked) {
            reDrawRoi_flag0 = true;
            setROIDisable0(0);
        } else {
            reDrawRoi_flag0 = false;
            setROIDisable0(1);
        }
        // 清除canvas
        ctx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
        redrawROI0();
        redrawROI1();
    }

    function check_roi_fun1() {
        if (this.checked) {
            reDrawRoi_flag1 = true;
            setROIDisable1(0);
        } else {
            reDrawRoi_flag1 = false;
            setROIDisable1(1);
        }
        console.log(reDrawRoi_flag1);
        // 清除canvas
        ctx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
        redrawROI0();
        redrawROI1();
    }

    check_roi_0.change(check_roi_fun0);
    check_roi_1.change(check_roi_fun1);

    // 目标函数，当图片尺寸改变时触发
    function func() {
        console.log('图片尺寸已改变！');
    }

    // 创建一个观察器实例并传入回调函数
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'style') {
                // 在这里调用你的函数
                func();
            }
        });
    });

    // 通过querySelector获取需要观察变化的图片元素
    var img = document.querySelector('#camera-image');

    // 配置观察选项:
    var config = {
        attributes: true,
        childList: true,
        subtree: true
    };

    // 传入目标节点和观察选项开始观察
    observer.observe(img, config);

    // 注意：这个方法依赖于style属性的变化来触发尺寸变化的检测。
    // 如果图片尺寸的改变不会影响其style属性，这种方法可能不会工作。


});
