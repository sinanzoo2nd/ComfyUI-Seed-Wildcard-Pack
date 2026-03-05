import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.Anima.DanbooruImporter",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DanbooruTagImporter") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }

                // 노드에 "태그 분석하기" 버튼 추가
                this.addWidget("button", "🔍 태그 분석 (API 호출)", "analyze", async () => {
                    // url 위젯 찾기
                    const urlWidget = this.widgets.find((w) => w.name === "url");
                    const previewWidget = this.widgets.find((w) => w.name === "preview_box");
                    
                    if (!urlWidget || !urlWidget.value) {
                        alert("Danbooru URL을 입력해주세요!");
                        return;
                    }

                    previewWidget.value = "분석 중... (최대 15초 소요될 수 있습니다)";
                    
                    try {
                        // Step 1에서 만든 파이썬 API 서버로 POST 요청
                        const response = await fetch('/anima/danbooru_analyze', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ url: urlWidget.value })
                        });

                        const result = await response.json();

                        if (result.status === "success") {
                            // 결과를 읽기 좋게 문자열로 포맷팅
                            let displayText = "✅ [분석 완료]\n\n";
                            for (const [cat, tags] of Object.entries(result.data)) {
                                displayText += `[${cat} (${tags.length}개)]\n${tags.join(", ")}\n\n`;
                            }
                            previewWidget.value = displayText;
                        } else {
                            previewWidget.value = "❌ 오류 발생:\n" + result.message;
                        }
                    } catch (error) {
                        previewWidget.value = "❌ 통신 오류:\n" + error.message;
                    }
                });
            };
        }
    }
});