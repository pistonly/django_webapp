    // Mouse Position and RGB Logic
    document.addEventListener('DOMContentLoaded', function() {
        const image = document.getElementById('camera-image');
        const coordsDisplay = document.getElementById('coords');

        // 确保图片已加载获取其真实尺寸
        image.onload = function() {
            const realWidth = this.naturalWidth;
            const realHeight = this.naturalHeight;
            console.log(realWidth, realHeight);

            roiCanvas.addEventListener('mousemove', function(e) {
                const rect = image.getBoundingClientRect();
                const scaleX = realWidth / rect.width; // 计算宽度的缩放比例
                const scaleY = realHeight / rect.height; // 计算高度的缩放比例
                const scale = Math.max(scaleX, scaleY)
                let offsetX = 0;
                let offsetY = 0;
                if (scaleX > scaleY) {
                    offsetX = 0;
                    offsetY = (rect.height * scale - realHeight) / 2;
                } else {
                    offsetX = (rect.width * scale - realWidth) / 2;
                    offsetY = 0;
                }
                const realX = (e.clientX - rect.left) * scale - offsetX; // 转换为真实尺寸上的X坐标
                const realY = (e.clientY - rect.top) * scale - offsetY; // 转换为真实尺寸上的Y坐标

                // 更新坐标显示
                coordsDisplay.textContent = `Coordinates: ${realX.toFixed(0)}, ${realY.toFixed(0)}`;
            });
        };
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
            }
        }

        function stopDrag() {
            isResizing = false;
            document.removeEventListener('mousemove', doDrag, false);
            document.removeEventListener('mouseup', stopDrag, false);
            // 确保canvas尺寸与图像相匹配
            roiCanvas.width = document.getElementById('camera-image').width;
            roiCanvas.height = document.getElementById('camera-image').height;
        }


        // ROI Selection Logic (simplified)
        // Additional logic needed for drawing and managing ROI selection
        // 确保canvas尺寸与图像相匹配
        roiCanvas.width = document.getElementById('camera-image').width;
        roiCanvas.height = document.getElementById('camera-image').height;

        function drawRect(x, y, width, height) {
            ctx.beginPath();
            ctx.rect(x, y, width, height);
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        roiCanvas.addEventListener('mousedown', (e) => {
            const rect = roiCanvas.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
            isDrawing = true;
        });

        roiCanvas.addEventListener('mousemove', (e) => {
            if (isDrawing) {
                const rect = roiCanvas.getBoundingClientRect();
                const currentX = e.clientX - rect.left;
                const currentY = e.clientY - rect.top;
                const width = currentX - startX;
                const height = currentY - startY;

                // 清除canvas
                ctx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
                drawRect(startX, startY, width, height);
            }
        });

        roiCanvas.addEventListener('mouseup', () => {
            isDrawing = false;
        });
    });

    function ROIButtonText0() {
        var button = document.getElementById("roi-button-0");
        if (button.textContent === "设置") {
            button.textContent = "确定";
        } else {
            button.textContent = "设置";
        }
    }

    function ROIButtonText1() {
        var button = document.getElementById("roi-button-1");
        if (button.textContent === "设置") {
            button.textContent = "确定";
        } else {
            button.textContent = "设置";
        }
    }
