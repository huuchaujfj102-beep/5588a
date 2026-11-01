# BLACK VELOCITY｜暗夜破界 — 13秒图生视频制作规范

**制作目标**：用用户提供的雨夜喷气超跑原始照片作为精确第一帧，生成一条电影级竖屏 9:16、13 秒、无旁白的极致速度短片。该车是原图中的概念/改装造型，任何马力、真实极速及推进原理均未得到证实，禁止填入虚构的厂家参数。

## 一、强制锁定的原图视觉真值

- 仅一台车：低矮、宽体、楔形黑色超跑，车头在画面左侧，尾部在右侧，前三分之四视角。
- 保持前保险杠攻击性造型、细锐白色 LED 灯、车身进气口、雨滴、黑色表面微观纹理、银灰轮毂及轮缘细小金色装饰。
- 保持右后部外露机械管状支架、外露后轮及唯一存在的向右侧后方喷射的蓝紫色喷气尾焰。禁止在轮胎或任何新增位置出现喷嘴。
- 赛道为夜间、降雨、积水反光、远处泛光灯、护栏、弯道红白路肩。禁止变白天或变更地理空间。
- 四轮/轮距/轴距和结构、车身所有线条及可见零件不得改动。禁止复制车辆、改变车头朝向、消失前大灯、增减轮数。

## 二、13秒时间轴

| 时间 | 镜头 | 车辆/物理动作 | 声音 |
|---|---|---|---|
| 0–3s | 以原图完全一致的前三分之四角度低机位侧向跟车，缓慢推进 | 水滴后掠，白色灯锋利，轮毂正确转动，轮胎向后切出薄水雾 | 发动机低频咆哮、雨点、湿胎摩擦 |
| 3–6s | 同侧稳定跟拍，略向后移动 | 现有尾部喷嘴蓝焰拉长，裸露支架轻振，车轮始终接地；沿既有弯道持续向前 | 机械增压音、喷气轰鸣逐渐叠加 |
| 6–10s | 镜头略靠近原有尾部喷气组件，不翻转或切换车的身份 | 单束尾焰中出现规律性蓝白色马赫菱形激波亮斑、局部热折射；护栏产生高速视差 | 喷气高频尖啸 + 厚实低频冲击 |
| 10–13s | 摄影车略落后，赛车持续沿同一轨迹远离，最终自然切黑 | 蓝光照亮水雾和路面，尾焰不断；不飞行，不瞬移，不转头 | 一次多普勒掠过感，尾音快速收束 |

注意：「马赫环/马赫菱形」仅为尾部高速喷流中可见的激波纹理，不意味着车辆自身必须达到超音速；不要画冲击波墙或科幻魔法圈。

## 三、图生视频七模块提示词（英文，可直接复制）

### 1. SOURCE IMAGE LOCK
Animate the provided image as the **literal opening frame** of one single 13-second 9:16 photoreal premium racing commercial. Preserve EXACTLY the same single black low-slung wedge-shaped hypercar, original left-facing front-three-quarter silhouette, sculpted nose, white angular LED headlights, front splitter, wet carbon-black surface, gold-edged wheel rims, visible exposed tubular rear framework and rear wheel assembly, existing SINGLE blue-violet jet exhaust extending backward toward screen-right. No changes to design, part count or proportions.

### 2. CONTROLLED VEHICLE MOVEMENT
The car remains on four rolling tires throughout, accelerates in the existing forward direction along the wet left-curving racetrack. Realistic wheel-rotation direction, suspension loading, razor-fine water spray, fast raindrop streaks and intense increasing parallax. Avoid violent spinning, drifting backwards or unmotivated jumps.

### 3. ENVIRONMENTAL DYNAMICS
Heavy rainy night, wet specular asphalt, track floodlights, dark barriers and red-white track curbs preserved from the reference image. Fine rain streaks, grounded road mist, blue reflections cast by exhaust and realistic turbulent spray. Background moves consistently with car motion.

### 4. CAMERA (ONE CONTINUOUS PHYSICALLY POSSIBLE TRACK)
0–3s low camera follows the original front-left three-quarter view; 3–6s stabilized side tracking closer to rear mechanical structure; 6–10s tightly follow the visible existing nozzle as the jet intensifies, maintaining visual recognition of the full car; 10–13s tracking vehicle lets the single car pull progressively away until a natural cut to black. No angle flip, no teleport, no reset of the original driving position.

### 5. LIGHT & EXHAUST EFFECTS
Single rear exhaust increases from deep cobalt to white-hot blue core with violet edges, authentic repeating Mach-diamond shock cells inside the plume, convincing heat shimmer gently distorting distant floodlights, never covering the car with fire. Cold track floodlights and white LED headlamp highlights contrast with blue jet reflections on wet road.

### 6. CINEMATOGRAPHIC QUALITY & AUDIO
Premium live-action photoreal racing film, cinematic dynamic range, sharply legible mechanical joints, tire treads and wet body microtexture, smooth stabilized low-rig photography, coherent speed blur in background and wheel spokes only; hero car always sharp. No spoken narration. Dominant throaty engine roar, turbine rise, mechanical vibration, wet tire hiss, jet thunder and final Doppler rush. Ambient musical sub-bass if any stays very quiet. Add the three Chinese characters “造镜者” only in post-production as subtle floating semitransparent watermark; never let video model invent any text.

### 7. NEGATIVE PROMPT
different car, altered silhouette, additional vehicle, body morph, duplicate wheels, missing wheels, jet emerging from wheels, new jet nozzles, unattached exhaust, altered rear support, headlights changed, mirrored car, opposite travel direction, flying car, teleporting, turning into a motorcycle, wet/dry scene mismatch, unrealistic water physics, bizarre rings around the entire car, fireballs, fantasy city, cartoon CGI, excessive motion blur hiding the car, heavy smoke concealing mechanical structure, flicker, warped perspective, logos, subtitles, watermark artifacts, AI generated text.

## 四、推荐渲染参数
- 起始资产：原始照片（857×1536，接近9:16），必须作第一帧。
- HeyGen Video 1；duration 13 秒；1080p；image-to-video。
- 输入参考比例保持原图；目标交付 9:16。应注意模型输出是按原图比例，后期可精确裁至标准 9:16。
- 推荐在合格视频上叠加“造镜者”三字：缓慢且不规则漂移，弱对比，约15%–22%不透明度；切勿遮住灯组/发动机。
- 保留发动机、喷气、轮胎、雨水主音效，无旁白，无配音。

## 五、影视工作站 QA — 生成后审核清单
- **ContinuityGuard**：单车身份、颜色、方向、前后零件和车轮数始终一致。
- **Physics & Spatial Audit**：喷焰只从原有尾喷嘴后喷，轮胎真实接地，轮旋和移动方向匹配；从未二次起步或瞬移。
- **MediaSpec**：准确13秒，竖屏9:16，音画同步；检查 fps / 编码 / 音量峰值。
- **OCR & Watermark**：生成素材中没有伪文字；后期“造镜者”淡漂浮，不能出现其他水印。
- **Audio Audit**：机械声为主，无无关旁白，人声音轨为零。
- **交付策略**：抽帧逐秒检查、失败先修复、测试合格后才考虑合并 main 或公开发行。

## 六、制作状态
- 原始图片已提交 HeyGen 图生视频任务，HeyGen video_id: `ce57224c2d7d4c4ca276bf0fad0e4a6a`。
- 项目创建时状态为 **processing**，不能宣称成片已经通过审核。
- 本文仅作为独立制作稿，相关 PR 必须等实际渲染和审核通过后再合并。
