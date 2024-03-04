
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

function setROI(x0, y0, x1, y1) {
    $.ajax({
        url: set_roi_url,
        type: 'POST',
        data: {
            camera_id: $('#select_camera').val(),
            x0: x0,
            y0: y0,
            x1: x1,
            y1: y1
        },
        beforeSend: function (xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function () {
            // 成功时的处理，例如显示一个消息
            console.log('roi setted');
        },
        error: function (xhr, status, error) {
            // 错误处理
            console.error('An error occurred: ' + error);
            $('#status').text('Error changing ae_state mode.');
        }
    });
}


// Mouse Position and RGB Logic
document.addEventListener('DOMContentLoaded', function() {
    const image = document.getElementById('camera-image');
    const coordsDisplay = document.getElementById('coords');

    // 确保图片已加载获取其真实尺寸
    image.onload = function() {
        realWidth = this.naturalWidth;
        realHeight = this.naturalHeight;

        // get current scale, offset
        updateScaleOffset();

        // debug 
        roiCanvas.addEventListener('mousemove', function(e) {
            const rect = image.getBoundingClientRect();
            const coor = getRealCoordinate(rect, e);
            // 更新坐标显示
            coordsDisplay.textContent = `Coordinates: ${coor[0]}, ${coor[1]}`;
        });
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
        if (roi_x0_0.val()) {
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
        if (roi_x0_1.val()) {
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
        if (roi_x0_1.val() && rect_color == 'red') {
            // draw roi-1
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

        if (roi_x0_0.val() && rect_color == 'green') {
            // draw roi-0
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
            // unfree roi-0
            check_roi_1.prop('disabled', false);
            roi_x0_1.prop('disabled', false);
            roi_y0_1.prop('disabled', false);
            roi_x1_1.prop('disabled', false);
            roi_y1_1.prop('disabled', false);
            roi_btn_1.prop('disabled', false);
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
            // unfree roi-0
            check_roi_0.prop('disabled', false);
            roi_x0_0.prop('disabled', false);
            roi_y0_0.prop('disabled', false);
            roi_x1_0.prop('disabled', false);
            roi_y1_0.prop('disabled', false);
            roi_btn_0.prop('disabled', false);
        }
    }

    roi_btn_0.click(function() {
        ROIButtonText0();
    });

    roi_btn_1.click(function() {
        ROIButtonText1();
    });

    check_roi_0.change(function () {
        if (this.checked && roi_x0_0.val()) {
            setROI(roi_x0_0.val(), roi_y0_0.val(), roi_x1_0.val(), roi_y1_0.val());
        }
    });

    check_roi_1.change(function () {
        if (this.checked && roi_x0_1.val()) {
            setROI(roi_x0_1.val(), roi_y0_1.val(), roi_x1_1.val(), roi_y1_1.val());
        }
    });

});



