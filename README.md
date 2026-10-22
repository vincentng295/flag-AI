# 🚩 Cướp Cờ Đáp Án AI

<img alt="banner" src="https://github.com/user-attachments/assets/1b1ce9cb-0317-492c-af5d-a41db91fcc45" />

Game chiến thuật đồng đội **1v1 → 5v5** chạy trên trình duyệt (điện thoại hoặc máy tính). Hai đội **Xanh** và **Đỏ** tranh nhau các lá cờ ghi đáp án A/B/C/D của một câu hỏi, rồi mang về căn cứ của mình để cắm. Hết giờ mới chấm: cờ nằm ở căn cứ đội nào thì đội đó được cộng hoặc trừ điểm.

Có ba chế độ phòng: **PvP** (hai đội người chơi), **PvE** (đội Xanh là người, đội Đỏ do máy điều khiển với số bot bằng số người đội Xanh) và **EvE** (demo: cả hai đội đều là bot, mọi người chỉ xem). Bot trong PvE **biết đáp án**: chỉ đi lấy hoặc cướp lá cờ đúng (lỡ nhặt nhầm cờ sai thì tự thả), rồi về cắm và ở lại giữ căn cứ. Khi địch cắm đúng lá cờ đáp án, cả đội bot đi men rìa bản đồ sang tập kết ngoài căn cứ địch, nhử và bắn hạ hiệp sĩ canh, rồi một bot cướp cờ còn các bot khác đứng quanh yểm trợ. Bot còn hộ tống đồng đội đang vác cờ, chạy tới bắn giúp đồng đội đang giao tranh và chặn địch xâm nhập căn cứ. Người vào sau khi phòng đầy có thể **xem trận** với tư cách khán giả.

## Chế độ EvE - máy đấu máy (demo)

Dùng để trình diễn game mà không cần người chơi. Khi tạo phòng, chọn **Chế độ: EvE**:

- Chọn số bot mỗi đội (1v1 → 5v5) và số round như phòng thường. Khi chủ phòng bấm **Bắt đầu**, máy tự lập đủ bot cho **cả hai đội** (tên ngẫu nhiên, không trùng).
- **Mọi người vào phòng, kể cả chủ phòng 👑, đều là khán giả.** Chủ phòng vẫn là người duy nhất bấm Bắt đầu và Tạm dừng. Không ai đổi sang đội Xanh/Đỏ được.
- Hai đội bot đều **biết đáp án** như bot của PvE, nên trận nào cũng là cuộc đua cướp cờ đúng giữa hai đội máy. Khán giả xem toàn bản đồ hoặc bấm tên một bot để theo sát (phím `←/→`, `V` về toàn map).
- Hết trận phòng về sảnh, chủ phòng bấm Bắt đầu để chạy trận demo mới. Khi người xem cuối cùng rời đi thì phòng tự đóng.

## Nhân vật và vũ khí

<img alt="gameplay" src="https://github.com/user-attachments/assets/3ef96bb8-373c-461a-8b7b-d9de50b846fd" />

| | |
|---|---|
| Nhân vật | 👦 Học sinh nam, 👧 Học sinh nữ (chọn ở sảnh) |
| Áo | Đội Xanh áo xanh, đội Đỏ áo đỏ |
| 🔫 Súng bong bóng nước | Bắn xa, đạn bay thẳng, 1 sát thương, hồi 0.32 giây. Có **tự ngắm**: đạn hút nhẹ về địch/quái gần tâm ngắm nhất, trong tầm và không bị tường chắn |
| 🗡️ Kiếm nhựa trẻ em | Chém hình quạt tầm gần (58 px), **2 sát thương**, hồi 0.55 giây. Trúng thì **đẩy lùi** và làm địch choáng, ngắt hành động của họ |
| 🚀 Súng tên lửa (mới) | Nhặt trên bản đồ, được **3 quả**. Tên lửa **tự dẫn** tới địch/quái gần nhất trong 460 px (không dò được người đang núp bụi cỏ), nổ lan bán kính 62 px, **3 sát thương**, hồi 0.8 giây. Tường chặn được tên lửa, khiên chặn được vụ nổ từ phía trước |
| 🛡️ Khiên | Chỉ dùng khi cầm kiếm. Giơ khiên chặn được đòn (đạn, kiếm, laze, quái) đến từ phía trước trong khoảng ±66°, nhưng đi chậm còn 60% |

Trúng 1 đòn súng mất 1 máu, trúng 1 nhát kiếm mất 2 máu (mặc định có 3 máu). Hết máu thì bị "đóng băng" 5 giây rồi hồi sinh ở căn cứ. Người đang vác cờ không bắn và không chém được.

Tầm đạn bong bóng được chọn đúng bằng tầm laze của thần giữ cờ (480 px), nên không thể đứng ngoài tầm laze mà bắn trúng thần.

## Quái vật, hiệp sĩ, EXP và cấp độ

<img alt="fullmap_gameplay" src="https://github.com/user-attachments/assets/c81472c6-77d6-4950-bac3-c29553e50e7d" />

- **Quái vật:** mỗi round có 8 quái nhỏ đặt đối xứng hai bên (🟢 slime chậm, 🦇 dơi nhanh) và 1 **Golem** ở giữa bản đồ. Quái đuổi người ở gần, chạm vào là mất máu (Golem mất 2). Bị hạ thì hồi sinh sau 25 giây (Golem 45 giây).
- **Thần giữ cờ 👁️:** mỗi lá cờ có 1 thần (25 máu, +80 điểm) đi dạo ngẫu nhiên quanh lá cờ. Nó ngắm người gần nhất trong 480 px, nạp 0.9 giây (có đường đỏ báo trước, khoá hướng ở 0.35 giây cuối) rồi bắn tia laze xuyên người, dừng ở tường, mất 2 máu, hồi chiêu 2.6 giây. Laze trúng cả hai đội. Bị bắn hoặc chém thì nó **đuổi theo người đó** cho tới khi họ chạy thoát, ngã, hoặc bị kéo quá xa cờ rồi mới quay về. Kiếm trúng sẽ ngắt ngay lượt nạp laze. Hạ được thì rớt nhiều EXP và luôn rớt ❤️, hồi sinh sau 45 giây.
- **Hiệp sĩ 🛡️ (mới):** mỗi đội có **5 hiệp sĩ** canh quanh căn cứ của mình, mang màu đội. Họ đi vòng chậm quanh căn cứ; địch lại gần căn cứ, hoặc bắn/chém trúng họ, thì họ lao ra đuổi đánh cận chiến (1 máu/đòn). Khi địch ở ngoài tầm cận chiến nhưng trong tầm 360 px và không bị tường chắn, hiệp sĩ vừa đuổi vừa **bắn súng bong bóng** (1 máu/viên, 1.4 giây/viên, không trúng quái trung lập, hạ người thì tính là "bởi quái vật"). Họ đuổi tới khi địch ngã, chạy thoát (cách hiệp sĩ hơn 520 px hoặc bị kéo quá xa căn cứ) rồi quay về chỗ gác quanh căn cứ. Hiệp sĩ có 6 máu, hạ được +25 điểm, rớt EXP và đôi khi ❤️. **Hiệp sĩ chết không hồi sinh** trong round đó (round sau được tạo lại đủ 5 con). Đòn của đội mình đi xuyên qua hiệp sĩ đội mình.
- **Điểm:** hạ slime +10, dơi +15, hiệp sĩ +25, Golem +60, thần giữ cờ +80, hạ một đối thủ +`POINTS_KILL` (mặc định 20). Điểm cộng cho cả đội và được tính vào cuối round cùng điểm cờ. Điểm hạ gục hiện nhỏ cạnh tổng điểm.
- **Rớt đồ ngẫu nhiên:** quái, hiệp sĩ và người bị hạ rớt 1-4 cục ⭐ EXP với giá trị ngẫu nhiên, đôi khi rớt thêm ❤️ hồi 1 máu (thần giữ cờ và Golem luôn rớt). Chạm vào để nhặt, ai nhặt trước người đó được. Đồ biến mất sau 25 giây.
- **Cấp độ (tối đa 5):** lên cấp cần `6 × cấp hiện tại` EXP. Mỗi cấp +1 máu tối đa (và hồi đầy máu), +4% tốc độ, kiếm dài thêm 4 px. Cấp độ reset mỗi round.

## Tim hồi máu, súng tên lửa và nâng cấp theo đội (mới)

- **💖 Tim hồi máu:** 6 tim đặt cố định, đối xứng quanh bản đồ (chấm hồng trên minimap). Ai thiếu máu chạm vào thì hồi 1 máu; tim đã nhặt hồi lại sau 20 giây (`HEART_RESPAWN`). Tim rớt từ quái/người bị hạ vẫn giữ nguyên như cũ.
- **🚀 Súng tên lửa:** 4 cây rải 4 góc bản đồ, đặt đối xứng (chấm cam trên minimap). Nhặt được 10 quả (bot cũng biết đi nhặt khi hết đạn), tự chuyển sang slot 3; hết đạn tự về súng bong bóng. Cây súng hiện lại sau 45 giây (`ROCKET_RESPAWN`). Đạn mất khi sang round mới.
- **💬 Chat:** nhấn `Enter` (hoặc nút 💬 góc trái trên) để mở khung chat; `Tab` hoặc nút 👥/🌐 đổi giữa kênh **Đội** (chỉ đồng đội thấy; khán giả chat với khán giả) và kênh **Cả map** (mọi người trong phòng). `Enter` gửi, `Esc` đóng. Tối đa 120 ký tự, cách nhau 0,6 giây/tin.
- **🤖 Bot dùng vũ khí:** khi hết đạn, bot (kể cả bot chơi thay người AFK) tự đi nhặt cây súng tên lửa gần nhất trong tầm ~1100 px (tối đa 2 bot cùng đội đi nhặt một cây). Có đạn thì bot bắn tên lửa vào người chơi địch (ưu tiên kẻ đang vác cờ), golem, hiệp sĩ địch và thần giữ cờ canh lá cờ bot đang nhắm tới (cần đường bắn không vướng tường, cách 90–420 px). Địch lọt vào tầm kiếm thì bot chuyển sang kiếm để chém, địch sắp tới gần thì bot áp sát để chém (trừ khi đang vác cờ/cắm cờ/cướp cờ). Xa hơn thì vẫn bắn súng bong bóng như cũ.
- **⬆️ Nâng cấp khi trả lời đúng:** đội nào cắm đúng cờ ở căn cứ khi hết round thì **round sau** được nâng 1 cấp, cộng dồn tối đa 3 cấp (`UPGRADE_MAX`), reset khi bắt đầu trận mới:

| Cấp | Máu tối đa | Súng bong bóng | Kiếm | Khiên (nửa góc chặn) |
|---|---|---|---|---|
| 0 | HP | 1 | 2 | 66° |
| 1 | HP+1 | 2 | 3 | 73° |
| 2 | HP+2 | 2 | 3 | 80° |
| 3 | HP+3 | 3 | 4 | 87° |

  Bảng ở đầu `main.py`: `GUN_DMG`, `SWORD_DMG_UP`, `SHIELD_ARC_UP`. Bong bóng của đội đã nâng cấp to hơn một chút để dễ nhận ra.
- **🎉 Kết thúc trận:** hiện lời chúc mừng đội thắng (có pháo giấy), người chơi xuất sắc nhất (điểm cao nhất) và bảng thống kê Điểm / Kill / Defeat / K/D của cả hai đội.

## Cách chơi

1. Mỗi round 3 phút: 10 giây đọc đề, 170 giây tranh cờ, rồi xem kết quả.
2. Mỗi cờ ứng với một đáp án. **Trong lúc chơi không ai biết cờ nào đúng.**
3. Nhặt cờ, vác về căn cứ và đứng yên cho thanh tiến trình đầy để cắm. Khi cắm xong, đội đó thấy thông báo **"HÃY BẢO VỆ LÁ CỜ!"**.
   - **Mỗi đội chỉ được mang về 1 lá cờ:** đội đã cắm cờ, hoặc đang có đồng đội vác cờ, thì không nhặt thêm cờ khác được.
   - **Nhổ cờ nhà:** cắm nhầm thì đứng cạnh lá cờ nhà đã cắm rồi bấm `G` (điện thoại: nút ⛏️ hiện ở chỗ nút thả cờ khi đứng gần cờ) và đứng yên khoảng 2 giây (`UNPLANT_SECONDS`) để nhổ lên. Cờ về vị trí gốc, đội đó không nhặt lại đúng lá ấy trong round này nên phải săn lá cờ khác. Mỗi đội nhổ tối đa 2 lần/round (`UNPLANT_MAX`). Bot không tự nhổ cờ.
   - Cờ đã cắm ở căn cứ đối phương vẫn cướp được bằng cách đứng cạnh cờ cho thanh tiến trình đầy (khoảng 2.5 giây), nhưng phải vượt qua hiệp sĩ canh ở đó. Bị cướp mất cờ thì đội đó được nhặt cờ khác.
4. Hết giờ, đội giữ cờ ở căn cứ: đáp án đúng **+100**, sai **−50**.
5. Bản đồ có 2 căn cứ ở 2 góc, 3 đường, sông chéo (đi chậm), rừng và bụi cỏ (núp, địch không thấy).
6. **Thông báo bên trái màn hình** cho cả hai đội và khán giả, ví dụ:
   - `X đã lấy lá cờ đáp án A`
   - `Y đã cướp lá cờ đáp án B khỏi team đỏ`
   - `X đã cắm lá cờ đáp án A ở căn cứ`, `X đã thả lá cờ đáp án A`
   - `Z đã bị đánh bại bởi Y`
   - `Y đã bị đánh bại bởi quái vật` (quái thường, hiệp sĩ hoặc laze của thần giữ cờ)
7. **Bảng thống kê:** bấm vào thanh điểm ở giữa phía trên màn hình (có biểu tượng 📊) để mở bảng tên người chơi từng đội với **Điểm, Kill, Defeat, K/D**. Bảng cũng có ở màn hình kết quả mỗi round và cuối trận (nút 📊 Thống kê). Số liệu tính cả trận và reset khi bắt đầu trận mới:
   - **Điểm:** điểm cá nhân từ hạ đối thủ (`POINTS_KILL`) và hạ quái (slime, dơi, hiệp sĩ, Golem, thần giữ cờ). Không gồm điểm cờ, vì điểm cờ tính cho cả đội.
   - **Kill:** số đối thủ đã hạ. **Defeat:** số lần bị hạ (kể cả bởi quái). **K/D:** Kill chia Defeat (Defeat = 0 thì chia cho 1).
8. **Bot chơi thay người vắng mặt:**
   - **AFK:** đứng yên, không di chuyển/bắn/đổi vũ khí quá 10 giây (đổi bằng `AFK_SECONDS`, `0` = tắt) thì bot chơi thay tạm thời; bấm di chuyển hoặc bắn là lấy lại quyền ngay. Đang cắm/cướp cờ (phải đứng yên) hoặc đang bị đóng băng thì không tính là AFK.
   - **Mất kết nối giữa trận:** nhân vật do bot điều khiển trong lúc chờ, được giữ chỗ 90 giây để vào lại (đổi bằng `REJOIN_SECONDS`). Hết thời gian chờ thì bot giữ nhân vật đó đến hết trận.
   - **Thoát trận / rời phòng giữa trận:** nhân vật không biến mất mà do bot điều khiển tiếp đến hết trận (tên có thêm 🤖, điểm số và thống kê giữ nguyên, cờ đang vác bot vác nốt).
   - Bot thay người **không tự đi nhặt cờ dưới đất**. Bot **chỉ đi cướp lá cờ đáp án đúng** khi địch đã cắm nó ở căn cứ họ (và đội mình chưa có cờ), cùng đồng đội công thành. Còn lại bot yểm trợ: canh căn cứ, đánh địch, đuổi người vác cờ, hộ tống và chạy tới hỗ trợ đồng đội đang giao tranh, mang nốt lá cờ đang vác. Địch cắm cờ sai thì bot không đi cướp. Bảng tin bên trái báo khi ai đó AFK, quay lại hoặc rời trận.

**Điều khiển**

- Máy tính: `W A S D` hoặc phím mũi tên để di chuyển, chuột để ngắm, `Space` hoặc bấm chuột trái để tấn công, phím **`1`** súng bong bóng, **`2`** kiếm gỗ, **`3`** súng tên lửa (`E` / `Q` đổi vũ khí lần lượt), **giữ chuột phải hoặc `Shift` để giơ khiên** (khi cầm kiếm), `G` để thả cờ / nhổ cờ nhà (khi đứng cạnh cờ đã cắm), `P` hoặc `Esc` để tạm dừng, `M` để tắt/bật âm thanh, bấm thanh điểm để xem thống kê (`Esc` để đóng).
- Điện thoại: cần trái để di chuyển, cần phải để ngắm và tự bắn, nút **1** 🔫 / **2** 🗡️ / **3** 🚀 (hiện số đạn) để chọn vũ khí, nút 🛡️ (kéo/giữ) để giơ khiên, nút 🏳️ để thả cờ (khi vác cờ) và đổi thành ⛏️ để nhổ cờ khi đứng gần lá cờ nhà đã cắm. Nên xoay ngang màn hình. Vị trí các nút có thể kéo chỉnh trong game.
- Chủ phòng 👑 là người duy nhất bấm Bắt đầu và Tạm dừng.

## Cài đặt

Cần Python 3.9 trở lên.

```bash
pip install -r requirements.txt
```

Các file cần nằm cùng một thư mục:

```
main.py              # máy chủ (trọng tài của game)
gunicorn.py          # chạy máy chủ bằng Gunicorn (khuyên dùng)
flag.html            # giao diện game
socket_io_min.js     # thư viện Socket.IO phía trình duyệt
question.json        # ngân hàng câu hỏi (không bị phục vụ ra web)
version.json         # phiên bản: chỉ client cùng phiên bản mới kết nối được
requirements.txt     # thư viện Python cần cài
.env.example     # mẫu cấu hình
```

> `socket_io_min.js` phải đặt cạnh `main.py` vì máy chủ phục vụ file này cho trình duyệt.

## Cấu hình

Sao chép mẫu cấu hình rồi sửa:

```bash
cp .env.example .env
```

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `HOST` | `0.0.0.0` | `127.0.0.1` chỉ máy này (dùng khi có tunnel), `0.0.0.0` cho cả lớp cùng Wi-Fi |
| `PORT` | `8889` | Cổng web |
| `ALLOWED_ORIGINS` | `*` | Nguồn được phép gọi, cách nhau bằng dấu phẩy |
| `ALLOWED_HOSTS` | `*` | Chỉ nhận request có header Host khớp (hỗ trợ `*.ten-mien.com`) |
| `QUESTION_FILE` | `./question.json` | Đường dẫn file câu hỏi |
| `VERSION_FILE` | `version.json` | File phiên bản |
| `TUNNEL` | `false` | Bật Cloudflare Tunnel |
| `TUNNEL_HOST` | | Tên miền của game (khi dùng tunnel có tài khoản) |
| `TUNNEL_TOKEN` | | Token tunnel. Để trống thì dùng tên miền tạm `trycloudflare.com` |
| `HTTPS_CERT`, `HTTPS_KEY` | | Chứng chỉ và khoá riêng để máy chủ tự phục vụ HTTPS |
| `TLS_HOST` | `0.0.0.0` | Địa chỉ lắng nghe HTTPS |
| `TLS_PORT` | `443` | Cổng HTTPS |
| `TLS_REFRESH_HOURS` | `12` | Tự tải lại chứng chỉ sau mỗi bấy nhiêu giờ (hữu ích khi cert gia hạn) |
| `MAX_SPECTATORS` | `30` | Số khán giả tối đa mỗi phòng |
| `REJOIN_SECONDS` | `90` | Giữ chỗ cho người mất kết nối giữa trận (giây), `0` = tắt |
| `READ_SECONDS` | `10` | Thời gian đọc đề |
| `PLAY_SECONDS` | `170` | Thời gian tranh cờ |
| `RESULT_SECONDS` | `12` | Thời gian hiện kết quả |
| `HP` | `3` | Số máu mỗi người |
| `DOWN_SECONDS` | `5` | Thời gian bị đóng băng sau khi hết máu |
| `POINTS_CORRECT` | `100` | Điểm khi cờ đúng |
| `POINTS_WRONG` | `-50` | Điểm khi cờ sai |
| `POINTS_KILL` | `20` | Điểm cho đội khi hạ một đối thủ |
| `HEART_RESPAWN` | `20` | Giây để tim trên bản đồ hiện lại sau khi bị nhặt |
| `ROCKET_RESPAWN` | `45` | Giây để súng tên lửa hiện lại sau khi bị nhặt |
| `UNPLANT_SECONDS` | `2` | Giây giữ yên để nhổ lá cờ nhà đã cắm |
| `UNPLANT_MAX` | `2` | Số lần nhổ cờ tối đa của mỗi đội trong một round |
| `UPGRADE_MAX` | `3` | Số cấp nâng cấp tối đa của một đội (tối đa 3 vì bảng sát thương có 4 mức) |

Nếu bật `TUNNEL` và đặt `ALLOWED_HOSTS` khác `*`, nhớ thêm `TUNNEL_HOST` vào danh sách.

Cân bằng nằm ở đầu `main.py`:

- Tên lửa và nâng cấp: `RK_AMMO`, `RK_SPEED`, `RK_TURN`, `RK_SEEK`, `RK_DMG`, `RK_SPLASH`, `RK_COOL`, `GUN_DMG`, `SWORD_DMG_UP`, `SHIELD_ARC_UP`; vị trí tim và súng: `HEART_SPOTS_T`, `RK_SPOTS_T` (toạ độ ô).
- Súng và kiếm: `BSPEED`, `COOL`, `SWORD_R`, `SWORD_COOL`, `SWORD_DMG`, `SHIELD_ARC`, `SHIELD_K`.
- Thần giữ cờ: `LASER_RANGE`, `LASER_CHARGE`, `LASER_CD`, `LASER_DMG`, `GUARD_*`.
- Hiệp sĩ: bảng `MON[4]` (máu, tốc độ, sát thương, điểm) và các hằng `KNIGHT_N`, `KNIGHT_RING`, `KNIGHT_SEE`, `KNIGHT_LEASH`, `KNIGHT_ORBIT`, `KNIGHT_GUN_RANGE`, `KNIGHT_GUN_CD`, `KNIGHT_LOSE`.

## Ngân hàng câu hỏi

`question.json` là một danh sách (hoặc đối tượng có khóa `questions`). Mỗi câu gồm đề, một đáp án đúng, các đáp án sai và lời giải thích. Mỗi lượt game lấy 1 đáp án đúng và tối đa 3 đáp án sai:

```json
[
  {
    "question": "Thủ đô của Việt Nam là gì?",
    "correct": "Hà Nội",
    "wrong": ["Huế", "Đà Nẵng", "TP. Hồ Chí Minh"],
    "explanation": "Hà Nội là thủ đô của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam."
  }
]
```

Cũng chấp nhận các khóa thay thế: `q`, `answer`, `wrongs`, `incorrect`, `explain`. Nếu không đọc được file, game dùng bộ câu hỏi dự phòng có sẵn.

## Chạy

```bash
python gunicorn.py   # khuyên dùng
python main.py       # máy chủ dev
```

Mở `http://127.0.0.1:8889/`. Với `HOST=0.0.0.0`, máy khác cùng Wi-Fi mở địa chỉ `http://<IP máy>:8889/` (máy chủ in sẵn địa chỉ này khi khởi động). Muốn chơi từ ngoài mạng, đặt `TUNNEL=true`, máy chủ sẽ tự tải và chạy `cloudflared`.

Các phần như chém, đẩy lùi, hiệp sĩ và thần giữ cờ đều do máy chủ quyết định, nên **phải chạy lại máy chủ sau khi cập nhật `main.py`**, và nhớ tăng `version` trong `version.json` để các tab cũ tải lại bản mới.
