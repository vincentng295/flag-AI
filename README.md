# 🚩 Cướp Cờ Đáp Án AI

Game chiến thuật đồng đội **1v1 → 5v5** chạy trên trình duyệt (điện thoại hoặc máy tính). Hai đội **Xanh** và **Đỏ** tranh nhau các lá cờ ghi đáp án A/B/C/D của một câu hỏi, rồi mang về căn cứ của mình để cắm. Hết giờ mới chấm: cờ nằm ở căn cứ đội nào thì đội đó được cộng hoặc trừ điểm.

## Nhân vật và vũ khí

| | |
|---|---|
| Nhân vật | 👦 Học sinh nam, 👧 Học sinh nữ (chọn ở sảnh) |
| Áo | Đội Xanh áo xanh, đội Đỏ áo đỏ |
| 🔫 Súng bong bóng nước | Bắn xa, đạn bay thẳng, hồi 0.32 giây |
| 🗡️ Kiếm nhựa trẻ em | Chém hình quạt tầm gần (58 px), hồi 0.55 giây |

Trúng 1 đòn mất 1 máu (mặc định 3 máu). Hết máu thì bị "đóng băng" 5 giây rồi hồi sinh ở căn cứ. Người đang vác cờ không bắn và không chém được.

## Quái vật, EXP và cấp độ

- **Quái vật:** mỗi round có 8 quái nhỏ đặt đối xứng hai bên (🟢 slime chậm, 🦇 dơi nhanh) và 1 **Golem** ở giữa bản đồ. Quái đuổi người ở gần, chạm vào là mất máu (Golem mất 2). Bị hạ thì hồi sinh sau 25 giây (Golem 45 giây).
- **Thần giữ cờ 👁️:** mỗi lá cờ có 1 thần đứng cạnh (25 máu, +80 điểm). Nó ngắm người gần nhất trong 480 px, nạp 0.9 giây (có đường đỏ báo trước, khoá hướng ở 0.35 giây cuối) rồi bắn tia laze xuyên người, dừng ở tường, mất 2 máu, hồi chiêu 2.6 giây. Laze trúng cả hai đội. Hạ được thì rớt nhiều EXP và luôn rớt ❤️, hồi sinh sau 45 giây.
- **Điểm:** hạ slime +10, dơi +15, Golem +60, hạ một đối thủ +`POINTS_KILL` (mặc định 20). Điểm cộng cho cả đội và được tính vào cuối round cùng điểm cờ. Điểm hạ gục hiện nhỏ cạnh tổng điểm.
- **Rớt đồ ngẫu nhiên:** quái và người bị hạ rớt 1-4 cục ⭐ EXP với giá trị ngẫu nhiên, đôi khi rớt thêm ❤️ hồi 1 máu (Golem luôn rớt). Chạm vào để nhặt, ai nhặt trước người đó được. Đồ biến mất sau 25 giây.
- **Cấp độ (tối đa 5):** lên cấp cần `6 × cấp hiện tại` EXP. Mỗi cấp +1 máu tối đa (và hồi đầy máu), +4% tốc độ, kiếm dài thêm 4 px. Cấp độ reset mỗi round.

## Cách chơi

1. Mỗi round 3 phút: 10 giây đọc đề, 170 giây tranh cờ, rồi xem kết quả.
2. Mỗi cờ ứng với một đáp án. **Trong lúc chơi không ai biết cờ nào đúng.**
3. Nhặt cờ, vác về căn cứ và đứng yên cho thanh tiến trình đầy để cắm.
4. Hết giờ, đội giữ cờ ở căn cứ: đáp án đúng **+100**, sai **−50**.
5. Bản đồ có 2 căn cứ ở 2 góc, 3 đường, sông chéo (đi chậm), rừng và bụi cỏ (núp, địch không thấy).

**Điều khiển**

- Máy tính: `W A S D` hoặc phím mũi tên để di chuyển, chuột để ngắm, `Space` hoặc bấm chuột để tấn công, `E` / `Q` để đổi vũ khí, `F` để thả cờ.
- Điện thoại: cần trái để di chuyển, cần phải để ngắm và tự bắn, nút 🔫/🗡️ ở góc trên trái để đổi vũ khí, nút 🏳️ (chỉ hiện khi đang vác cờ) để thả cờ. Nên xoay ngang màn hình.
- Chủ phòng 👑 là người duy nhất bấm Bắt đầu và Tạm dừng.

## Cài đặt

Cần Python 3.9 trở lên.

```bash
pip install -r requirements.txt
```

Các file cần nằm cùng một thư mục:

```
main.py              # máy chủ (trọng tài của game)
flag.html            # giao diện game
socket_io_min.js     # thư viện Socket.IO phía trình duyệt
question.json        # ngân hàng câu hỏi (không bị phục vụ ra web)
.env.example         # mẫu cấu hình
_env.example         # mẫu cấu hình
```

> `socket_io_min.js` phải đặt cạnh `main.py` vì máy chủ phục vụ file này cho trình duyệt. Dùng lại file của game Rắn Săn Đáp Án AI nếu bạn đã có.

## Cấu hình

Sao chép mẫu cấu hình rồi sửa:

```bash
cp .env.example .env
cp _env.example flag.env
```

Máy chủ mặc định đọc file `.env`. Nếu dùng tên `flag.env`, hãy chỉ định:
Máy chủ mặc định đọc file `.env`. Nếu dùng tên `flag.env` (để chạy song song với game rắn), hãy chỉ định:

```bash
ENV_FILE=flag.env python main.py
```

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `HOST` | `0.0.0.0` | `127.0.0.1` chỉ máy này (dùng khi có tunnel), `0.0.0.0` cho cả lớp cùng Wi-Fi |
| `PORT` | `8889` | Cổng web |
| `ALLOWED_ORIGINS` | `*` | Nguồn được phép gọi, cách nhau bằng dấu phẩy |
| `ALLOWED_HOSTS` | `*` | Chỉ nhận request có header Host khớp (hỗ trợ `*.ten-mien.com`) |
| `QUESTION_FILE` | `./question.json` | Đường dẫn file câu hỏi |
| `TUNNEL` | `false` | Bật Cloudflare Tunnel |
| `TUNNEL_HOST` | | Tên miền của game (khi dùng tunnel có tài khoản) |
| `TUNNEL_TOKEN` | | Token tunnel. Để trống thì dùng tên miền tạm `trycloudflare.com` |
| `READ_SECONDS` | `10` | Thời gian đọc đề |
| `PLAY_SECONDS` | `170` | Thời gian tranh cờ |
| `RESULT_SECONDS` | `12` | Thời gian hiện kết quả |
| `HP` | `3` | Số máu mỗi người |
| `DOWN_SECONDS` | `5` | Thời gian bị đóng băng sau khi hết máu |
| `POINTS_CORRECT` | `100` | Điểm khi cờ đúng |
| `POINTS_WRONG` | `-50` | Điểm khi cờ sai |
| `POINTS_KILL` | `20` | Điểm cho đội khi hạ một đối thủ |

Nếu bật `TUNNEL` và đặt `ALLOWED_HOSTS` khác `*`, nhớ thêm `TUNNEL_HOST` vào danh sách.

Cân bằng vũ khí nằm ở đầu `main.py`: `BSPEED`, `COOL` cho súng, `SWORD_R`, `SWORD_COOL` cho kiếm.

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
python main.py
```

Mở `http://127.0.0.1:8889/`. Với `HOST=0.0.0.0`, máy khác cùng Wi-Fi mở địa chỉ `http://<IP máy>:8889/` (máy chủ in sẵn địa chỉ này khi khởi động). Muốn chơi từ ngoài mạng, đặt `TUNNEL=true`, máy chủ sẽ tự tải và chạy `cloudflared`.
- Kiếm cần chạy lại `main.py` sau khi cập nhật, vì phần chém nằm ở máy chủ.
