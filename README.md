# 🚩 Cướp Cờ Đáp Án AI

<img alt="banner" src="https://github.com/user-attachments/assets/1b1ce9cb-0317-492c-af5d-a41db91fcc45" />

Game chiến thuật đồng đội **1v1 → 5v5** chạy trên trình duyệt (điện thoại hoặc máy tính). Hai đội **Xanh** và **Đỏ** tranh nhau các lá cờ ghi đáp án A/B/C/D của một câu hỏi, rồi mang về căn cứ của mình để cắm. Hết giờ mới chấm: cờ nằm ở căn cứ đội nào thì đội đó được cộng hoặc trừ điểm.

Có hai chế độ phòng: **PvP** (hai đội người chơi) và **PvE** (đội Xanh là người, đội Đỏ do máy điều khiển với số bot bằng số người đội Xanh). Bot trong PvE **biết đáp án**: chỉ đi lấy hoặc cướp lá cờ đúng, rồi về cắm và ở lại giữ căn cứ. Người vào sau khi phòng đầy có thể **xem trận** với tư cách khán giả.

## Nhân vật và vũ khí

<img alt="gameplay" src="https://github.com/user-attachments/assets/3ef96bb8-373c-461a-8b7b-d9de50b846fd" />

| | |
|---|---|
| Nhân vật | 👦 Học sinh nam, 👧 Học sinh nữ (chọn ở sảnh) |
| Áo | Đội Xanh áo xanh, đội Đỏ áo đỏ |
| 🔫 Súng bong bóng nước | Bắn xa, đạn bay thẳng, 1 sát thương, hồi 0.32 giây. Có **tự ngắm**: đạn hút nhẹ về địch/quái gần tâm ngắm nhất, trong tầm và không bị tường chắn |
| 🗡️ Kiếm nhựa trẻ em | Chém hình quạt tầm gần (58 px), **2 sát thương**, hồi 0.55 giây. Trúng thì **đẩy lùi** và làm địch choáng, ngắt hành động của họ |
| 🛡️ Khiên | Chỉ dùng khi cầm kiếm. Giơ khiên chặn được đòn (đạn, kiếm, laze, quái) đến từ phía trước trong khoảng ±66°, nhưng đi chậm còn 60% |

Trúng 1 đòn súng mất 1 máu, trúng 1 nhát kiếm mất 2 máu (mặc định có 3 máu). Hết máu thì bị "đóng băng" 5 giây rồi hồi sinh ở căn cứ. Người đang vác cờ không bắn và không chém được.

Tầm đạn bong bóng được chọn đúng bằng tầm laze của thần giữ cờ (480 px), nên không thể đứng ngoài tầm laze mà bắn trúng thần.

## Quái vật, hiệp sĩ, EXP và cấp độ

<img alt="fullmap_gameplay" src="https://github.com/user-attachments/assets/c81472c6-77d6-4950-bac3-c29553e50e7d" />

- **Quái vật:** mỗi round có 8 quái nhỏ đặt đối xứng hai bên (🟢 slime chậm, 🦇 dơi nhanh) và 1 **Golem** ở giữa bản đồ. Quái đuổi người ở gần, chạm vào là mất máu (Golem mất 2). Bị hạ thì hồi sinh sau 25 giây (Golem 45 giây).
- **Thần giữ cờ 👁️:** mỗi lá cờ có 1 thần (25 máu, +80 điểm) đi dạo ngẫu nhiên quanh lá cờ. Nó ngắm người gần nhất trong 480 px, nạp 0.9 giây (có đường đỏ báo trước, khoá hướng ở 0.35 giây cuối) rồi bắn tia laze xuyên người, dừng ở tường, mất 2 máu, hồi chiêu 2.6 giây. Laze trúng cả hai đội. Bị bắn hoặc chém thì nó **đuổi theo người đó** cho tới khi họ chạy thoát, ngã, hoặc bị kéo quá xa cờ rồi mới quay về. Kiếm trúng sẽ ngắt ngay lượt nạp laze. Hạ được thì rớt nhiều EXP và luôn rớt ❤️, hồi sinh sau 45 giây.
- **Hiệp sĩ 🛡️ (mới):** mỗi đội có **5 hiệp sĩ** canh quanh căn cứ của mình, mang màu đội. Họ đi vòng chậm quanh căn cứ; địch lại gần căn cứ, hoặc bắn/chém trúng họ, thì họ lao ra đánh cận chiến (1 máu/đòn), đuổi tới khi địch ngã, chạy thoát hoặc bị kéo quá xa căn cứ rồi quay về chỗ gác. Hiệp sĩ có 6 máu, hạ được +25 điểm, rớt EXP và đôi khi ❤️. **Hiệp sĩ chết không hồi sinh** trong round đó (round sau được tạo lại đủ 5 con). Đòn của đội mình đi xuyên qua hiệp sĩ đội mình.
- **Điểm:** hạ slime +10, dơi +15, hiệp sĩ +25, Golem +60, thần giữ cờ +80, hạ một đối thủ +`POINTS_KILL` (mặc định 20). Điểm cộng cho cả đội và được tính vào cuối round cùng điểm cờ. Điểm hạ gục hiện nhỏ cạnh tổng điểm.
- **Rớt đồ ngẫu nhiên:** quái, hiệp sĩ và người bị hạ rớt 1-4 cục ⭐ EXP với giá trị ngẫu nhiên, đôi khi rớt thêm ❤️ hồi 1 máu (thần giữ cờ và Golem luôn rớt). Chạm vào để nhặt, ai nhặt trước người đó được. Đồ biến mất sau 25 giây.
- **Cấp độ (tối đa 5):** lên cấp cần `6 × cấp hiện tại` EXP. Mỗi cấp +1 máu tối đa (và hồi đầy máu), +4% tốc độ, kiếm dài thêm 4 px. Cấp độ reset mỗi round.

## Cách chơi

1. Mỗi round 3 phút: 10 giây đọc đề, 170 giây tranh cờ, rồi xem kết quả.
2. Mỗi cờ ứng với một đáp án. **Trong lúc chơi không ai biết cờ nào đúng.**
3. Nhặt cờ, vác về căn cứ và đứng yên cho thanh tiến trình đầy để cắm. Khi cắm xong, đội đó thấy thông báo **"HÃY BẢO VỆ LÁ CỜ!"**.
   - **Mỗi đội chỉ được mang về 1 lá cờ:** đội đã cắm cờ, hoặc đang có đồng đội vác cờ, thì không nhặt thêm cờ khác được.
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
8. Người chơi mất kết nối giữa trận được giữ chỗ 90 giây để vào lại (đổi bằng `REJOIN_SECONDS`).

**Điều khiển**

- Máy tính: `W A S D` hoặc phím mũi tên để di chuyển, chuột để ngắm, `Space` hoặc bấm chuột trái để tấn công, `E` / `Q` để đổi vũ khí, **giữ chuột phải hoặc `Shift` để giơ khiên** (khi cầm kiếm), `F` để thả cờ, `P` hoặc `Esc` để tạm dừng, `M` để tắt/bật âm thanh, bấm thanh điểm để xem thống kê (`Esc` để đóng).
- Điện thoại: cần trái để di chuyển, cần phải để ngắm và tự bắn, nút 🔫/🗡️ để đổi vũ khí, nút 🛡️ (kéo/giữ) để giơ khiên, nút 🏳️ (chỉ hiện khi đang vác cờ) để thả cờ. Nên xoay ngang màn hình. Vị trí các nút có thể kéo chỉnh trong game.
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

Nếu bật `TUNNEL` và đặt `ALLOWED_HOSTS` khác `*`, nhớ thêm `TUNNEL_HOST` vào danh sách.

Cân bằng nằm ở đầu `main.py`:

- Súng và kiếm: `BSPEED`, `COOL`, `SWORD_R`, `SWORD_COOL`, `SWORD_DMG`, `SHIELD_ARC`, `SHIELD_K`.
- Thần giữ cờ: `LASER_RANGE`, `LASER_CHARGE`, `LASER_CD`, `LASER_DMG`, `GUARD_*`.
- Hiệp sĩ: bảng `MON[4]` (máu, tốc độ, sát thương, điểm) và các hằng `KNIGHT_N`, `KNIGHT_RING`, `KNIGHT_SEE`, `KNIGHT_LEASH`, `KNIGHT_ORBIT`.

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
