import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "SeedWildcard.SafetyLevelSelector",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "SafetyLevelNode") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                // 기존 노드 생성 로직 실행
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                // setTimeout을 사용하여 노드와 위젯이 완전히 렌더링된 직후에 제어권을 가져옵니다.
                setTimeout(() => {
                    const randomModeWidget = this.widgets?.find((w) => w.name === "random_mode");
                    const levelWidget = this.widgets?.find((w) => w.name === "level");
                    const uncensoredWidget = this.widgets?.find((w) => w.name === "uncensored");

                    // 위젯이 아직 생성되지 않았다면 중단
                    if (!randomModeWidget || !levelWidget || !uncensoredWidget) return;

                    const updateWidgets = (isRandom) => {
                        if (isRandom) {
                            // 원래 설정 백업
                            levelWidget.origType = levelWidget.type;
                            levelWidget.origComputeSize = levelWidget.computeSize;
                            uncensoredWidget.origType = uncensoredWidget.type;
                            uncensoredWidget.origComputeSize = uncensoredWidget.computeSize;

                            // ComfyUI 표준 숨김 트릭: type을 hidden으로 바꾸고 크기를 0으로 만듦
                            levelWidget.type = "hidden";
                            levelWidget.computeSize = () => [0, -4];
                            uncensoredWidget.type = "hidden";
                            uncensoredWidget.computeSize = () => [0, -4];
                        } else {
                            // 원래 타입과 크기 복구
                            if (levelWidget.origType) {
                                levelWidget.type = levelWidget.origType;
                                levelWidget.computeSize = levelWidget.origComputeSize;
                            }
                            if (uncensoredWidget.origType) {
                                uncensoredWidget.type = uncensoredWidget.origType;
                                uncensoredWidget.computeSize = uncensoredWidget.origComputeSize;
                            }
                        }
                        
                        // 변경된 위젯 상태를 바탕으로 노드 크기 재계산 및 UI 강제 새로고침
                        this.setSize(this.computeSize());
                        app.graph.setDirtyCanvas(true, true);
                    };

                    // 토글 스위치를 누를 때마다 실행될 콜백
                    randomModeWidget.callback = (value) => {
                        updateWidgets(value);
                    };

                    // 처음 로드되었을 때 현재 상태(Value)를 즉시 반영
                    updateWidgets(randomModeWidget.value);
                }, 10); // 10ms 지연으로 확실한 안정성 확보

                return r;
            };
        }
    },
});