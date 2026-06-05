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

                // 버튼 이름을 우회한다는 의미로 조금 수정했습니다.
                this.addWidget("button", "🔍 태그 분석 (브라우저 직접 호출)", "analyze", async () => {
                    const urlWidget = this.widgets.find((w) => w.name === "url");
                    const previewWidget = this.widgets.find((w) => w.name === "preview_box");
                    
                    if (!urlWidget || !urlWidget.value) {
                        alert("Danbooru URL을 입력해주세요!");
                        return;
                    }

                    // 🌟 1. URL에서 Post ID를 추출합니다.
                    const match = urlWidget.value.match(/\/posts\/(\d+)/);
                    if (!match) {
                        alert("유효한 Danbooru URL이 아닙니다.");
                        return;
                    }
                    const postId = match[1];

                    previewWidget.value = "브라우저가 직접 분석 중... (Cloudflare 우회 중 🕵️)";
                    app.graph.setDirtyCanvas(true);
                    
                    try {
                        // 🌟 2. [핵심] 파이썬을 배제하고 크롬 브라우저가 직접 단부루 호출!
                        const db_response = await fetch(`https://danbooru.donmai.us/posts/${postId}.json`);
                        if (!db_response.ok) throw new Error("HTTP " + db_response.status);

                        // Cloudflare를 무사히 통과하고 받아온 순수 JSON 데이터
                        const raw_data = await db_response.json();

                        // 🌟 3. 가져온 순수 데이터를 파이썬 백엔드로 전송 (분류 및 캐싱을 부탁함)
                        const response = await fetch('/anima/danbooru_analyze', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                url: urlWidget.value,
                                raw_data: raw_data // 🔥 파이썬에게 이 데이터를 던져줍니다!
                            })
                        });

                        const result = await response.json();

                        if (result.status === "success") {
                            // 🌟 4. 기존 코드의 훌륭했던 결과 포맷팅(문자열 조합) 그대로 유지!
                            let displayText = "✅ [분석 및 캐시 저장 완료]\n\n";
                            for (const [cat, tags] of Object.entries(result.data)) {
                                displayText += `[${cat} (${tags.length}개)]\n${tags.join(", ")}\n\n`;
                            }
                            previewWidget.value = displayText;
                        } else {
                            previewWidget.value = "❌ 백엔드 저장 오류:\n" + result.message;
                        }
                    } catch (error) {
                        previewWidget.value = "❌ 브라우저 직접 통신 차단됨:\n" + error.message;
                    }
                    
                    app.graph.setDirtyCanvas(true);
                });
            };
        }
    }
});