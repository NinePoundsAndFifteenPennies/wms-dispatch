# API 鎺ュ彛鏂囨。

鍚庣浣跨敤 FastAPI 骞跺湪 `/docs` 鑷姩鐢熸垚浜嗗畬鏁寸殑 OpenAPI Swagger 椤甸潰銆傛湰鏂囨。琛ュ厖璁板綍鏍稿績涓氬姟 API 鐨勪紶鍙備笌鏍煎紡瑙勮寖銆?

## 缁熶竴鍝嶅簲缁撴瀯

闄や笅杞界瓑鐗规畩鎺ュ彛澶栵紝绯荤粺鍝嶅簲缁熶竴绾︽潫濡備笅锛?

```json
{
  "code": 200,
  "message": "ok",
  "data": {}
}
```

- 鎴愬姛鍝嶅簲锛歚code = HTTP 鐘舵€佺爜`锛沗message = "ok"`
- 澶辫触鍝嶅簲锛歚code = HTTP 鐘舵€佺爜`锛沗message = 閿欒鎻忚堪`锛沗data` 鍙兘涓?`null` 鎴栨牎楠岄敊璇槑缁?

---

## 鏃堕棿涓庢椂鍖鸿鑼?

涓洪伩鍏嶅墠鍚庣鍜屾暟鎹簱鍑虹幇鏃跺尯鍋忓樊锛岀郴缁熺粺涓€閲囩敤浠ヤ笅瑙勫垯锛?

1. 涓氬姟鏃堕棿缁熶竴浠ヤ腑鍥藉寳浜椂闂达紙`Asia/Shanghai`锛孶TC+8锛変负鍙ｅ緞銆?
2. 鏁版嵁搴撳瓨鍌ㄧ被鍨嬬粺涓€涓?`TIMESTAMP(0) WITHOUT TIME ZONE`锛屽惈涔夋槸鈥滃寳浜椂闂存湰鍦版椂闂粹€濄€?
3. API 杩斿洖鏃堕棿瀛楃涓茬粺涓€涓虹绾ф牸寮忥細`YYYY-MM-DDTHH:mm:ss`锛堜笉甯?`Z`锛夈€?
4. 鍓嶇鍦ㄨВ鏋愭绫诲瓧绗︿覆鏃讹紝蹇呴』鎸夊寳浜椂闂磋涔夎В鏋愶紝涓嶅緱鎸夋祻瑙堝櫒鏈湴鏃跺尯榛樿鎺ㄦ柇銆?
5. 璁よ瘉渚嬪锛欽WT 鐨?`exp` 閲囩敤 UTC 鏃堕棿鎴筹紙鏍囧噯鍋氭硶锛夛紝涓嶇撼鍏ヤ笟鍔℃椂闂村彛寰勩€?


---

## 璁よ瘉鎺ュ彛 (Auth)

### 鐧诲綍绛惧彂 Token

閫氳繃鐢ㄦ埛鍚嶅瘑鐮侀獙璇佸苟鑾峰彇 JWT銆?

```http
POST /api/auth/login
```

**璇锋眰浣?(JSON):**

| 瀛楁 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| username | string | 鐧诲綍鐢ㄦ埛鍚?|
| password | string | 瀵嗙爜鏄庢枃 |

**鎴愬姛鍝嶅簲:** `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@wms.local",
    "role": "admin",
    "warehouse_id": null,
    "is_active": true
  }
}
```

**璇存槑:**
- 澶辫触鐘舵€佺爜锛歚401` 瀵嗙爜閿欒, `403` 璐︽埛琚鐢?


### 鑾峰彇褰撳墠鐢ㄦ埛淇℃伅

鎻愬彇璇锋眰澶翠腑鐨?Token 骞惰В鏋愬嚭鐧诲綍浜哄憳鐨勫畬鏁翠笟鍔′俊鎭€?

```http
GET /api/auth/me
```

**璇锋眰澶?** `Authorization: Bearer <token>`

**鎴愬姛鍝嶅簲:** `200 OK`
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@wms.local",
  "role": "admin",
  "warehouse_id": null,
  "is_active": true
}
```

---

## 绠＄悊鍛樻ā鍧楁帴鍙?(Admin)

### 鑾峰彇鐢ㄦ埛鍒楄〃 (甯﹀垎椤典笌鎼滅储)

鑾峰彇绯荤粺鍐呯鐞嗕汉鍛樸€佽皟搴﹀憳涓庡伐浜虹殑鍒楄〃銆?

```http
GET /api/admin/users
```

**鏌ヨ鍙傛暟:**

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| page | int | 1 | 褰撳墠椤电爜锛屾渶灏忎负1 |
| page_size | int | 10 | 姣忛〉鏉℃暟锛?~100 涔嬮棿 |
| search | string | - | 鏍规嵁鐢ㄦ埛鍚嶆垨閭杩涜鐨勬ā绯婃悳绱㈣瘝 |

**鎴愬姛鍝嶅簲:** `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@test.com",
      "role": "admin",
      "is_active": true,
      "warehouse_id": null,
      "skill_picking": 0,
      "skill_staging": 0,
      "skill_shipping": 0
    },
    {
      "id": 2,
      "username": "worker_li",
      "email": "li@test.com",
      "role": "worker",
      "is_active": true,
      "warehouse_id": 1,
      "skill_picking": 5,
      "skill_staging": 3,
      "skill_shipping": 1
    }
  ],
  "total": 42
}
```

**瀛楁璇存槑 (items):**

| 瀛楁 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| id | int | 鐢ㄦ埛鍞竴鏍囪瘑 |
| username | string | 鐢ㄦ埛鍚?|
| email | string | 閭鍦板潃 |
| role | string | 鐢ㄦ埛瑙掕壊 (admin, dispatcher, worker) |
| is_active | boolean | 褰撳墠璐︽埛鏄惁鍏佽鐧诲綍婵€娲?|
| warehouse_id | int | 鎵€灞炵殑浠撳簱ID (绠＄悊鍛樹负 null) |
| skill_picking | int | 鎷ｈ揣鎶€鑳界瓑绾?|
| skill_staging | int | 澶囪揣鎶€鑳界瓑绾?|
| skill_shipping| int | 鍙戣揣鎶€鑳界瓑绾?|

---

### 鍒涘缓绠＄悊浜哄憳

鏂板缓绯荤粺鐢ㄦ埛銆傞渶瑕佺鍚堜弗鏍肩殑瀛楁涓庝笟鍔¤鍒欐牎楠屻€?

```http
POST /api/admin/users
```

**璇锋眰浣?(JSON):**

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| username | string | 鏄?| 鐢ㄦ埛鍚嶏紙鍏ㄥ眬鍞竴锛?|
| email | string(email)| 鏄?| 閭鍦板潃锛堟牸寮忎弗鏍兼牎楠岋級 |
| password | string | 鏄?| 瀵嗙爜鏄庢枃 |
| role | string | 鏄?| 鏋氫妇鍊硷細admin, dispatcher, worker |
| warehouse_id | int | 鍚?| 闈炵鐞嗗憳姝ら」蹇呭～ |
| skill_picking | int | 鍚?| 鎷ｈ揣鑳藉姏鐐癸紝榛樿 0 |
| skill_staging | int | 鍚?| 澶囪揣鑳藉姏鐐癸紝榛樿 0 |
| skill_shipping | int | 鍚?| 鍙戣揣鑳藉姏鐐癸紝榛樿 0 |

**鎴愬姛鍝嶅簲:** `201 Created`
```json
{
  "id": 15,
  "username": "new_worker",
  "email": "new@wms.local",
  "role": "worker",
  "is_active": true,
  "warehouse_id": 2,
  "skill_picking": 2,
  "skill_staging": 0,
  "skill_shipping": 0
}
```

**璇存槑:**
- 閭鎴栫敤鎴峰悕閲嶅灏嗚繑鍥?`400 Bad Request`銆?
- 闈炵鐞嗗憳濡傛灉 `warehouse_id` 缂哄け灏嗘姏鍑烘姤閿欍€?

---

### 鏇存柊鐢ㄦ埛淇℃伅

淇敼鎸囧畾鐢ㄦ埛鐨勫睘鎬у€硷紝鏀寔灞€閮ㄦ洿鏂帮紙鏈紶瀛楁灏嗕繚鎸佸師鏍凤級銆?

```http
PUT /api/admin/users/{id}
```

**璺緞鍙傛暟:**

| 鍙傛暟 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| id | int | 瑕佹洿鏂扮殑鐢ㄦ埛ID |

**璇锋眰浣?(JSON):** 
*(鍏ㄥ瓧娈典负鍙€夛紝浼犱粈涔堟洿鏂颁粈涔?*

| 瀛楁 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| username | string | 鏂扮敤鎴峰悕 |
| email | string(email)| 鏂伴偖绠卞湴鍧€ |
| role | string | 瑙掕壊淇敼 |
| warehouse_id | int | 浠撳簱褰掑睘淇敼 |
| skill_picking | int | 鎷ｈ揣鑳藉姏鐐逛慨鏀?|
| skill_staging | int | 澶囪揣鑳藉姏鐐逛慨鏀?|
| skill_shipping | int | 鍙戣揣鑳藉姏鐐逛慨鏀?|

**鎴愬姛鍝嶅簲:** `200 OK`
*(杩斿洖鏇存柊鍚庣殑 User 瀵硅薄锛岀粨鏋勫悓 Create 鍝嶅簲涓€鑷?*

---

### 鏇存敼鐢ㄦ埛鍚仠鐘舵€?

寮€鍚垨绂佺敤鏌愯处鍙凤紙绂佺敤鎬佷笅鐨勭敤鎴峰皢鏃犳硶鐧诲綍绯荤粺鎴栨墽琛屽姩浣滐級銆?

```http
PATCH /api/admin/users/{id}/status
```

**璺緞鍙傛暟:**

| 鍙傛暟 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| id | int | 瑕佸皝绂佹垨鍚敤鐨勭敤鎴稩D |

**璇锋眰浣?(JSON):**

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| is_active | boolean | 鏄?| true 涓哄惎鐢紝false 涓虹鐢?|

**鎴愬姛鍝嶅簲:** `200 OK`
*(杩斿洖鏇存柊鍚庣殑 User 瀵硅薄)*

**璇存槑:**
- **涓氬姟瑙勫垯:** 濡傛灉灏濊瘯灏?`role="admin"` 鐨勪汉鐘舵€佽缃负 `false`锛屾帴鍙ｅ皢鎷︽埅骞惰繑鍥?`400 Admin account cannot be disabled`銆?

---

### 鎵归噺绂佺敤鐢ㄦ埛

鎵归噺灏嗙敤鎴疯涓虹鐢ㄧ姸鎬侊紙杞鐢紝涓嶅垹闄ゆ暟鎹級銆?

```http
POST /api/admin/users/batch-disable
```

**璇锋眰浣?(JSON):**

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| ids | int[] | 鏄?| 闇€瑕佺鐢ㄧ殑鐢ㄦ埛 ID 鍒楄〃 |

**鎴愬姛鍝嶅簲:** `200 OK`
```json
{
  "disabled": 3
}
```

**璇存槑:**
- 绠＄悊鍛樿处鍙蜂笉浼氳鎵归噺绂佺敤锛堝悗绔細鑷姩蹇界暐 `role="admin"` 璐﹀彿锛夈€?

---

### 鑾峰彇鍏ㄩ儴浠撳偍鍒楄〃

鑾峰彇鐢ㄤ簬閫夐」涓嬫媺绛夌敤閫旂殑鍩虹鍦扮悊浠撳偍缃戠偣淇℃伅銆?

```http
GET /api/admin/warehouses
```

**鎴愬姛鍝嶅簲:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "鍖椾含涓績鍛ㄨ浆浠?
  },
  {
    "id": 2,
    "name": "涓婃捣鍒嗘嫧璋冮厤绔?
  }
]
```

**瀛楁璇存槑:**

| 瀛楁 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| id | int | 浠撳簱鍞竴缂栧彿 |
| name | string | 浠撳簱瀵瑰鏄剧ず鍚嶇О |

---

### 浠撳簱搴撳瓨绠＄悊锛堟柊澧烇級

```http
GET    /api/admin/warehouses/{warehouse_id}/inventory
PATCH  /api/admin/warehouses/{warehouse_id}/inventory/{inventory_id}/stocktake
POST   /api/admin/warehouses/{warehouse_id}/inventory/inbound
```

#### 1) 鑾峰彇浠撳簱搴撳瓨璇︽儏

```http
GET /api/admin/warehouses/{warehouse_id}/inventory?page=1&page_size=10&search=鍏抽敭璇?
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| page | int | 1 | 褰撳墠椤电爜锛屾渶灏忎负1 |
| page_size | int | 10 | 姣忛〉鏉℃暟锛?~100 涔嬮棿 |
| search | string | - | 鎸夊晢鍝佸悕绉?/ SKU / 绫诲埆妯＄硦鎼滅储 |

**鎴愬姛鍝嶅簲:** `200 OK`
```json
{
  "warehouse": {
    "id": 1,
    "name": "鍖椾含涓績鍛ㄨ浆浠?,
    "address": "鍖椾含甯傛湞闃冲尯...",
    "cover_image": "/resources/warehouses/w1.png",
    "description": "鍗庡寳鍖哄煙涓讳粨",
    "is_active": true
  },
  "items": [
    {
      "id": 21,
      "product_id": 8,
      "sku": "SKU-10086",
      "product_name": "鏍囧噯绾哥",
      "category": "鍖呰鐗╂枡",
      "product_cover_image": "/resources/products/p8.png",
      "product_is_active": true,
      "qty_on_hand": 120,
      "qty_reserved": 10,
      "qty_locked": 5,
      "qty_threshold": 30,
      "qty_available": 105
    }
  ],
  "total": 1
}
```

#### 2) 鐩樼偣淇搴撳瓨

```http
PATCH /api/admin/warehouses/{warehouse_id}/inventory/{inventory_id}/stocktake
```

**璇锋眰浣?(JSON):**

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| qty_on_hand | int | 鍚?| 淇鍚庣殑鐜板瓨閲忥紙>= 0锛?|
| qty_threshold | int | 鍚?| 淇鍚庣殑搴撳瓨闃堝€硷紙>= 0锛?|
| reason | string | 鍚?| 淇鍘熷洜锛屾渶闀?500 瀛?|

**璇存槑锛?*
- `qty_on_hand` 涓?`qty_threshold` 鑷冲皯浼犱竴涓€?
- 褰撲紶鍏?`qty_on_hand` 鏃讹紝鍚庣浼氭牎楠岋細`qty_on_hand >= qty_reserved + qty_locked`銆?
- 涓婅堪鏍￠獙绛変环浜庣‘淇濅慨姝ｅ悗 `qty_available = qty_on_hand - qty_reserved - qty_locked` 涓嶄负璐熴€?
- `qty_available` 鏄暟鎹簱鐢熸垚鍒楋紙`GENERATED ALWAYS AS (qty_on_hand - qty_reserved - qty_locked) STORED`锛夛紝浼氶殢鐜板瓨閲忚嚜鍔ㄩ噸绠楋紝鎺ュ彛涓嶄細涔熶笉鑳界洿鎺ュ啓鍏ヨ瀛楁銆?
- 绂佺敤浠撳簱涓庝笅鏋跺晢鍝佷笉鍏佽鐩樼偣淇銆?
- 淇浼氬啓鍏?`stocktakes` 涓?`inventory_movements`銆?

#### 3) 杩涜揣鍏ュ簱

```http
POST /api/admin/warehouses/{warehouse_id}/inventory/inbound
```

**璇锋眰浣?(JSON):**

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| product_id | int | 鏄?| 杩涜揣鍟嗗搧 ID |
| qty | int | 鏄?| 杩涜揣鏁伴噺锛? 0锛?|
| reason | string | 鍚?| 鍙€夎鏄庯紝鏈€闀?500 瀛?|

**璇存槑锛?*
- 鑻ヤ粨搴撲腑涓嶅瓨鍦ㄨ鍟嗗搧搴撳瓨璁板綍锛岀郴缁熶細鑷姩鍒涘缓涓€鏉″簱瀛樿褰曞悗鍐嶇疮鍔犲叆搴撴暟閲忋€?
- 鍏ュ簱浼氬啓鍏?`stocktakes` 涓?`inventory_movements`锛岀敤浜庡悗缁璁′笌杩借釜銆?
- 绂佺敤浠撳簱涓庝笅鏋跺晢鍝佷笉鍏佽杩涜揣銆?

#### 4) 搴撳瓨娴佹按璁板綍锛堣秼鍔?+ 鏃ヨ妭鐐硅鎯咃級

```http
GET /api/admin/warehouses/inventory-movements/trends?days=14
GET /api/admin/warehouses/{warehouse_id}/inventory-movements/node-details?date=YYYY-MM-DD&page=1&page_size=20
```

**缁熻鍙ｅ緞璇存槑锛?*
- 璇ラ〉闈㈢粺璁′粎璁＄畻鐪熷疄搴撳瓨鍙樺寲锛歚delta_on_hand != 0`銆?
- `delta_reserved` 涓?`delta_locked` 浠呯敤浜庝笟鍔″唴閮ㄧ姸鎬佺鐞嗭紝涓嶇撼鍏ユ祦姘磋秼鍔跨粺璁°€?

**瓒嬪娍鎺ュ彛鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| days | int | 14 | 缁熻澶╂暟锛?~90 |

**瓒嬪娍鎺ュ彛鎴愬姛鍝嶅簲绀轰緥锛?*

```json
{
  "warehouses": [
    {
      "warehouse_id": 1,
      "warehouse_name": "鍗庝笢涓€鍙锋€讳粨",
      "points": [
        {
          "date": "2026-03-18",
          "movement_count": 5,
          "total_abs_delta": 132
        }
      ]
    }
  ]
}
```

**鏃ヨ妭鐐硅鎯呮煡璇㈠弬鏁帮細**

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| date | date | - | 鎸囧畾鏃ユ湡锛坄YYYY-MM-DD`锛?|
| page | int | 1 | 褰撳墠椤电爜 |
| page_size | int | 20 | 姣忛〉鏉℃暟锛?~100 |

**鏃ヨ妭鐐硅鎯呭搷搴旇鐐癸細**
- `total_abs_delta = SUM(ABS(delta_on_hand))`
- `positive_delta_on_hand = SUM(delta_on_hand > 0)`
- `negative_delta_on_hand_abs = SUM(ABS(delta_on_hand < 0))`
- `items` 涓哄綋鏃ュ師瀛愯妭鐐癸紝鏀寔鍓嶇鎸夋椂闂村簭鍒楃粯鍒剁偣浣嶅浘銆?
- `related_description` 涓轰笟鍔″寲鏂囨锛堣鍗曞彿銆佽皟鎷?from/to銆丼KU銆佹暟閲忋€佸師鍥犵瓑锛夈€?

**鏃ヨ妭鐐硅鎯呮垚鍔熷搷搴旂ず渚嬶紙鑺傞€夛級锛?*

```json
{
  "warehouse_id": 1,
  "warehouse_name": "鍗庝笢涓€鍙锋€讳粨",
  "date": "2026-03-18",
  "movement_count": 5,
  "total_abs_delta": 132,
  "positive_delta_on_hand": 80,
  "negative_delta_on_hand_abs": 52,
  "items": [
    {
      "id": 901,
      "created_at": "2026-03-18T10:31:02",
      "change_type": "ship_deduct",
      "product_id": 8,
      "product_sku": "SKU-10086",
      "product_name": "鏍囧噯绾哥",
      "delta_on_hand": -10,
      "related_type": "order",
      "related_id": 3001,
      "related_description": "璁㈠崟 ORD-20260318-0001锛涘娉細鍔犳€ュ彂璐?,
      "operated_by_name": "disp_chen"
    }
  ],
  "total": 5
}
```

---

### 瀹㈡埛绠＄悊锛堟柊澧烇級

```http
GET    /api/admin/customers
POST   /api/admin/customers
PUT    /api/admin/customers/{customer_id}
DELETE /api/admin/customers/{customer_id}
POST   /api/admin/customers/batch-delete
PATCH  /api/admin/customers/{customer_id}/status
```

**璇存槑锛?*
- `PATCH /status` 璇锋眰浣擄細`{"is_active": true|false}`銆?
- 瀹㈡埛鍒楄〃杩斿洖瀛楁鍚?`is_active`锛屽墠绔彲灞曠ず鍋滅敤璁板綍骞惰繘琛屾仮澶嶃€?

---

### 浜у搧绠＄悊锛堟柊澧烇級

```http
GET    /api/admin/products
GET    /api/admin/products/{product_id}
POST   /api/admin/products
PUT    /api/admin/products/{product_id}
DELETE /api/admin/products/{product_id}
POST   /api/admin/products/batch-delete
PATCH  /api/admin/products/{product_id}/status
POST   /api/admin/products/{product_id}/image
DELETE /api/admin/products/{product_id}/image
```

**璇︽儏鎺ュ彛璇存槑锛?*
- `GET /api/admin/products/{product_id}`锛氳繑鍥炲崟涓骇鍝佽鎯咃紝瀛楁缁撴瀯鍚屼骇鍝佸垪琛?`items[]` 鍏冪礌銆?

**鍥剧墖鎺ュ彛璇存槑锛?*
- 涓婁紶鍥剧墖锛歚POST /image`锛宍multipart/form-data`锛屽瓧娈靛悕涓?`image`銆?
- 绉婚櫎鍥剧墖锛歚DELETE /image`锛屼細灏嗘暟鎹簱 `cover_image` 娓呯┖锛屽苟鍒犻櫎鏈嶅姟鍣ㄦ枃浠躲€?
- 鏇存崲鍥剧墖锛氶噸澶嶈皟鐢ㄤ笂浼犳帴鍙ｅ嵆鍙紝绯荤粺浼氭浛鎹?URL 骞舵竻鐞嗘棫鍥炬枃浠躲€?

---

### 璁㈠崟绠＄悊锛堟柊澧烇級

```http
GET    /api/admin/orders
GET    /api/admin/orders/{order_id}
POST   /api/admin/orders
GET    /api/admin/orders/export
GET    /api/admin/orders/{order_id}/export
```

#### 1) 璁㈠崟鍒楄〃

```http
GET /api/admin/orders?page=1&page_size=10&search=鍏抽敭璇?status=in_progress&start_date=2026-03-01&end_date=2026-03-19
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| page | int | 1 | 褰撳墠椤碉紝鏈€灏?1 |
| page_size | int | 10 | 姣忛〉鏉℃暟锛?~100 |
| search | string | - | 璁㈠崟鍙?瀹㈡埛鍚嶇О妯＄硦鎼滅储 |
| status | string | - | `pending_acceptance \| in_progress \| completed \| cancelled` |
| start_date | string(date) | - | 鍒涘缓鏃堕棿璧峰鏃ユ湡 |
| end_date | string(date) | - | 鍒涘缓鏃堕棿缁撴潫鏃ユ湡 |

#### 2) 鍒涘缓璁㈠崟

```http
POST /api/admin/orders
```

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| customer_id | int | 鏄?| 瀹㈡埛 ID锛堝繀椤讳负鏈夋晥涓旀縺娲诲鎴凤級 |
| priority | string | 鍚?| `high \| medium \| low`锛岄粯璁?`medium` |
| description | string | 鍚?| 澶囨敞 |
| items | array | 鏄?| 鏄庣粏鏁扮粍锛岃嚦灏?1 鏉?|

`items[]` 瀛楁锛?
- `product_id`锛氫骇鍝?ID锛堝繀椤诲瓨鍦ㄤ笖 `is_active=true`锛?
- `qty`锛氭暟閲忥紝> 0
- `unit_price`锛氬崟浠凤紙鍒嗭級锛?= 0

#### 3) 璁㈠崟瀵煎嚭锛堟寜褰撳墠绛涢€夌粨鏋滐級

```http
GET /api/admin/orders/export?export_format=csv|markdown|pdf
```

**璇存槑锛?*
- `csv`锛歚text/csv; charset=utf-8`锛屽唴瀹瑰凡甯?UTF-8 BOM锛孍xcel 鎵撳紑涓枃涓嶄贡鐮併€?
- `markdown`锛歚text/markdown; charset=utf-8`銆?
- `pdf`锛歚application/pdf`锛屽搷搴?`data.content_base64` 涓?PDF 鐨?base64 鍐呭銆?

#### 4) 璁㈠崟璇︽儏 PDF 瀵煎嚭

```http
GET /api/admin/orders/{order_id}/export?export_format=pdf
```

**璇存槑锛?*
- 杩斿洖 `application/pdf`锛屽搷搴?`data.content_base64` 涓鸿鍗曡鎯?PDF 鐨?base64 鍐呭銆?

---

### 绠＄悊鎺у埗鍙版€昏锛堟柊澧烇級

```http
GET /api/admin/dashboard-overview
GET /api/admin/dashboard-overview/warehouse-performance/{warehouse_id}
```

#### 1) 鑾峰彇鎬昏鑱氬悎鏁版嵁

```http
GET /api/admin/dashboard-overview
```

**璇存槑锛?*
- 杩斿洖绠＄悊鍛樻€昏椤垫墍闇€鐨勮仛鍚堟寚鏍囦笌鍥捐〃鏁版嵁锛堣鍗曡繍钀ュ彛寰勶紝涓嶅惈宸ュ崟瓒嬪娍鍥撅級銆?
- `product_popularity` 浠呯粺璁?`status = completed` 鐨勮鍗曟槑缁嗐€?

**鎴愬姛鍝嶅簲绀轰緥锛堣妭閫夛級**
```json
{
  "kpis": {
    "pending_acceptance_orders": 8,
    "low_stock_alerts": 5,
    "cancelled_orders_today": 2,
    "accepted_no_dispatch_orders": 3
  },
  "warehouse_order_performance": [
    {
      "warehouse_id": 1,
      "warehouse_name": "鍖椾含涓績鍛ㄨ浆浠?,
      "total_orders": 188,
      "completed_orders": 160,
      "completion_rate": 85
    }
  ],
  "product_popularity": [
    {
      "product_id": 12,
      "sku": "SKU-12001",
      "product_name": "鍖荤敤鍙ｇ僵",
      "total_qty": 1320,
      "order_count": 94
    }
  ]
}
```

#### 2) 鑾峰彇浠撳簱涓嬭皟搴﹀憳璁㈠崟缁╂晥

```http
GET /api/admin/dashboard-overview/warehouse-performance/{warehouse_id}
```

**璺緞鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| warehouse_id | int | 浠撳簱 ID |

**璇存槑锛?*
- 鐢ㄤ簬鎬昏椤碘€滀粨搴撹鍗曞畬鎴愮巼鈥濆浘鐐瑰嚮涓嬮捇銆?
- 杩斿洖浠撳簱姹囨€伙紙鎬诲崟閲?瀹屾垚鍗曢噺/瀹屾垚鐜囷級鍜岃皟搴﹀憳鏄庣粏銆?

---

## 璋冨害鍛樻ā鍧楁帴鍙ｏ紙Dispatcher锛?

> 璁よ瘉瑕佹眰锛氫互涓嬫帴鍙ｅ潎闇€ `Authorization: Bearer <token>`锛屼笖褰撳墠鐢ㄦ埛瑙掕壊蹇呴』涓?`dispatcher`銆?

```http
GET  /api/dispatcher/orders
GET  /api/dispatcher/orders/{order_id}
POST /api/dispatcher/orders/{order_id}/accept
GET  /api/dispatcher/my-orders
GET  /api/dispatcher/my-orders/{order_id}
GET  /api/dispatcher/dashboard-summary
GET  /api/dispatcher/inventory
GET  /api/dispatcher/inventory-movements/trend
GET  /api/dispatcher/inventory-movements/node-details
GET  /api/dispatcher/work-orders
```

### 1) 鎺ュ崟涓績鍒楄〃锛堝緟鎺ュ崟锛?

```http
GET /api/dispatcher/orders?search=鍏抽敭璇?
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| search | string | - | 鎸夎鍗曞彿/瀹㈡埛鍚嶇О妯＄硦鎼滅储 |

**璇存槑锛?*
- 浠呰繑鍥?`status = pending_acceptance` 鐨勮鍗曘€?
- 杩斿洖缁撴瀯锛歚{ items: DispatcherOrderListItem[], total: number }`銆?

### 2) 鎺ュ崟涓績璇︽儏

```http
GET /api/dispatcher/orders/{order_id}
```

**璇存槑锛?*
- 浠呭厑璁告煡鐪嬪緟鎺ュ崟鑼冨洿鍐呰鍗曘€?
- 杩斿洖鍖呭惈瀹㈡埛鑱旂郴鏂瑰紡銆佽鍗曟槑缁嗐€侀樁娈典俊鎭笌宸ュ崟姹囨€汇€?

### 3) 鎺ュ崟鍔ㄤ綔

```http
POST /api/dispatcher/orders/{order_id}/accept
```

**璇存槑锛?*
- 鎴愬姛鍚庤鍗曡繘鍏ュ凡鎺ュ崟娴佺▼锛坄in_progress`锛夛紝骞跺畬鎴愭帴鍗曟椂搴忓瓧娈垫洿鏂般€?
- 鎺ュ崟杩囩▼鎵ц搴撳瓨鍙敤閲忔牎楠屼笌棰勭暀锛屽苟鍒濆鍖栭樁娈典俊鎭€?
- 杩斿洖鏈€鏂拌鍗曡鎯呭璞★紙缁撴瀯鍚岃鎯呮帴鍙ｏ級銆?
- 鑻ュ簱瀛樺彲鐢ㄩ噺涓嶈冻锛岃繑鍥?`400`锛屽苟鍦?`data.shortages` 涓粰鍑洪€愬晢鍝佺己鍙ｆ槑缁嗭紙鍩轰簬 `available` 瀵规瘮锛夈€?

**搴撳瓨涓嶈冻澶辫触鍝嶅簲绀轰緥 (`400`)锛?*

```json
{
  "code": 400,
  "message": "鍙敤搴撳瓨涓嶈冻锛岃鍏堣皟鎷ㄨˉ璐у悗鍐嶆帴鍗?,
  "data": {
    "shortages": [
      {
        "product_id": 8,
        "sku": "SKU-10086",
        "product_name": "鏍囧噯绾哥",
        "required_qty": 20,
        "available_qty": 6,
        "shortage_qty": 14
      }
    ]
  }
}
```

### 4) 鎴戠殑璁㈠崟鍒楄〃

```http
GET /api/dispatcher/my-orders?search=鍏抽敭璇?
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| search | string | - | 鎸夎鍗曞彿/瀹㈡埛鍚嶇О妯＄硦鎼滅储 |

**璇存槑锛?*
- 浠呰繑鍥炲綋鍓嶇櫥褰曡皟搴﹀憳鏈汉璁㈠崟锛歚status in (in_progress, completed, cancelled)`銆?
- 杩斿洖缁撴瀯锛歚{ items: DispatcherOrderListItem[], total: number }`銆?

### 5) 鎴戠殑璁㈠崟璇︽儏

```http
GET /api/dispatcher/my-orders/{order_id}
```

**璇存槑锛?*
- 浠呭厑璁告煡鐪嬪綋鍓嶇櫥褰曡皟搴﹀憳鏈汉宸叉帴璁㈠崟銆?
- 杩斿洖鍖呭惈瀹㈡埛鑱旂郴鏂瑰紡銆佽鍗曟槑缁嗐€侀樁娈电姸鎬併€佸伐鍗曟眹鎬荤瓑灞ョ害淇℃伅銆?

### 6) 璋冨害鍛樺伐浣滃彴姹囨€?

```http
GET /api/dispatcher/dashboard-summary
```

**鎴愬姛鍝嶅簲绀轰緥锛?*

```json
{
  "warehouse_id": 1,
  "warehouse_name": "鍖椾含涓績鍛ㄨ浆浠?,
  "pending_count": 12,
  "my_orders_count": 18,
  "my_in_progress_count": 9,
  "my_completed_count": 7,
  "my_cancelled_count": 2
}
```

**璇存槑锛?*
- 鐢ㄤ簬璋冨害鍛樺竷灞€椤堕儴鐘舵€佸窘鏍囥€佷晶杈规爮鈥滄垜鐨勮鍗曗€濇暟瀛椼€佸伐浣滃彴鑱氬悎缁熻灞曠ず銆?

### 7) 璋冨害鍛樺簱瀛樹腑蹇冿紙鍙锛?

```http
GET /api/dispatcher/inventory?page=1&page_size=10&search=鍏抽敭璇?
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| page | int | 1 | 褰撳墠椤电爜锛屾渶灏?1 |
| page_size | int | 10 | 姣忛〉鏉℃暟锛?~100 |
| search | string | - | 鎸変骇鍝佸悕绉?/ SKU / 绫诲埆妯＄硦鎼滅储 |

**鎴愬姛鍝嶅簲绀轰緥锛?*

```json
{
  "warehouse": {
    "id": 1,
    "name": "鍖椾含涓績鍛ㄨ浆浠?,
    "address": "鍖椾含甯傛湞闃冲尯...",
    "description": "鍗庡寳鍖哄煙涓讳粨",
    "cover_image": "/resources/warehouse_covers/warehouse_1.png",
    "is_active": true
  },
  "items": [
    {
      "id": 21,
      "product_id": 8,
      "sku": "SKU-10086",
      "product_name": "鏍囧噯绾哥",
      "category": "鍖呰鐗╂枡",
      "product_cover_image": "/resources/products/p8.png",
      "product_is_active": true,
      "qty_on_hand": 120,
      "qty_reserved": 10,
      "qty_locked": 5,
      "qty_threshold": 30,
      "qty_available": 105
    }
  ],
  "total": 1
}
```

**璇存槑锛?*
- 杩斿洖褰撳墠鐧诲綍璋冨害鍛樻墍灞炰粨搴撶殑搴撳瓨鍒嗛〉鍒楄〃銆?
- 璇ユ帴鍙ｄ负鍙鎺ュ彛锛屼笉鎻愪緵鐩樼偣淇/杩涜揣绛夊啓鎿嶄綔銆?

### 8) 璋冨害鍛樻湰浠撴祦姘磋褰?

```http
GET /api/dispatcher/inventory-movements/trend?days=14
GET /api/dispatcher/inventory-movements/node-details?date=YYYY-MM-DD&page=1&page_size=20
```

**缁熻鍙ｅ緞璇存槑锛?*
- 浠呯粺璁?`delta_on_hand != 0` 鐨勮褰曪紙鐪熷疄搴撳瓨鍙樺姩锛夈€?
- `delta_reserved`銆乣delta_locked` 涓嶅弬涓庢祦姘寸粺璁°€?

#### 8.1 鏈粨娴佹按瓒嬪娍

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| days | int | 14 | 缁熻澶╂暟锛?~90 |

**鎴愬姛鍝嶅簲绀轰緥锛?*

```json
{
  "warehouse_id": 1,
  "warehouse_name": "鍗庝笢涓€鍙锋€讳粨",
  "points": [
    {
      "date": "2026-03-18",
      "movement_count": 5,
      "total_abs_delta": 132
    }
  ]
}
```

#### 8.2 鏈粨鏃ヨ妭鐐硅鎯?

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| date | date | - | 鎸囧畾鏃ユ湡锛坄YYYY-MM-DD`锛?|
| page | int | 1 | 褰撳墠椤电爜 |
| page_size | int | 20 | 姣忛〉鏉℃暟锛?~100 |

**杩斿洖缁撴瀯瑕佺偣锛?*
- `total_abs_delta`锛氱粷瀵瑰€兼€诲彉鍖栭噺銆?
- `positive_delta_on_hand`锛氬綋鏃ョ幇瀛樻鍚戝彉鍖栭噺锛堝叆搴撴柟鍚戯級銆?
- `negative_delta_on_hand_abs`锛氬綋鏃ョ幇瀛樿礋鍚戝彉鍖栭噺缁濆鍊硷紙鍑哄簱鏂瑰悜锛夈€?
- `items[].related_description`锛氫笟鍔″寲璇存槑鏂囨锛屼究浜庣洿鎺ヤ綔涓烘搷浣滄棩蹇楅槄璇汇€?

### 9) 璋冨害鍛樺彲閫夊伐浜哄垪琛?

```http
GET /api/dispatcher/workers?search=鍏抽敭璇?
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| search | string | - | 鎸夌敤鎴峰悕妯＄硦鎼滅储宸ヤ汉 |

**璇存槑锛?*
- 浠呰繑鍥炲綋鍓嶈皟搴﹀憳鎵€灞炰粨搴撲笅鐨?`worker` 瑙掕壊鐢ㄦ埛銆?
- 杩斿洖瀛楁鍖呭惈涓夐樁娈垫妧鑳斤細`skill_picking/skill_staging/skill_shipping`銆?
- 杩斿洖瀛楁鏂板锛?
  - `active_work_order_count`锛氬伐浜哄綋鍓嶅湪閫斿伐鍗曟暟锛坄pending + in_progress`锛?
  - `active_work_order_limit`锛氬湪閫斿伐鍗曢槇鍊硷紙璇诲彇鍚庣閰嶇疆 `DISPATCHER_ACTIVE_WORK_ORDER_LIMIT`锛?

### 10) 璋冨害鍛樻淳鍗曢鏍￠獙锛堟柊澧烇級

```http
POST /api/dispatcher/orders/{order_id}/work-orders/precheck
```

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| stage_id | int | 鏄?| 璁㈠崟闃舵 ID |
| worker_id | int | 鏄?| 宸ヤ汉 ID |

**鎴愬姛鍝嶅簲绀轰緥锛?*

```json
{
  "stage_id": 21,
  "stage_type": "picking",
  "required_skill_min": 2,
  "required_skill_max": 6,
  "worker_skill": 4,
  "active_work_order_count": 5,
  "active_work_order_limit": 5,
  "has_risk": true,
  "risks": [
    {
      "code": "skill_gap",
      "message": "褰撳墠宸ヤ汉闃舵鎶€鑳?4)浣庝簬璇ラ樁娈垫渶楂樻妧鑳借姹?6)"
    },
    {
      "code": "worker_overload",
      "message": "褰撳墠宸ヤ汉鍦ㄩ€斿伐鍗曟暟(5)宸茶揪鍒颁笂闄?5)"
    }
  ],
  "skill_products": [
    {
      "product_id": 8,
      "product_sku": "SKU-10086",
      "product_name": "鏍囧噯绾哥",
      "required_skill": 6,
      "worker_skill": 4,
      "is_qualified": false
    }
  ]
}
```

**璇存槑锛?*
- 鑻?`worker_skill < required_skill_min`锛屽悗绔繑鍥?`400`锛岃宸ヤ汉绂佹娲惧崟銆?
- 鑻?`required_skill_min <= worker_skill < required_skill_max`锛岃繑鍥炴妧鑳介闄╋紙`skill_gap`锛夛紝鍏佽寮哄埗娲惧崟銆?
- 鑻?`worker_skill >= required_skill_max`锛屾妧鑳界淮搴︽棤椋庨櫓銆?
- 璐熻浇椋庨櫓鍒ゅ畾锛歚active_work_order_count >= active_work_order_limit`銆?

### 11) 璋冨害鍛樿鍗曞伐鍗曞垪琛?

```http
GET /api/dispatcher/orders/{order_id}/work-orders?stage_id=12&status=in_progress
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| stage_id | int | - | 鎸夐樁娈?ID 杩囨护 |
| status | string | - | `pending \| in_progress \| completed \| terminated` |

**璇存槑锛?*
- 浠呭厑璁歌闂綋鍓嶈皟搴﹀憳鏈汉璁㈠崟銆?
- 杩斿洖缁撴瀯锛歚{ items: DispatcherOrderWorkOrderResponse[], total: number }`銆?

### 12) 璋冨害鍛樺垱寤哄伐鍗?

```http
POST /api/dispatcher/orders/{order_id}/work-orders
```

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| stage_id | int | 鏄?| 璁㈠崟闃舵 ID |
| worker_id | int | 鏄?| 宸ヤ汉 ID |
| priority | string | 鍚?| `high \| medium \| low`锛岄粯璁?`medium` |
| deadline | string(datetime) | 鍚?| 鎴鏃堕棿 |
| description | string | 鍚?| 宸ュ崟澶囨敞 |
| override_reason | string | 鍚?| 瀛樺湪椋庨櫓鏃跺繀濉紱寮哄埗娲惧崟鍘熷洜 |

**璇存槑锛?*
- 閬靛惊闃舵涓茶涓庡叧闂ㄨ鍒欙細宸插畬鎴愰樁娈典笉鑳芥柊寤哄伐鍗曪紝涓嬩竴闃舵闇€涓婁竴闃舵瀹屾垚鍚庢墠鍙垱寤恒€?
- 鑻ラ鏍￠獙瀛樺湪椋庨櫓涓旀湭浼?`override_reason`锛屽垱寤烘帴鍙ｈ繑鍥?`400`銆?
- 椋庨櫓鏀捐鏃讹紝绯荤粺浼氬皢缁撴瀯鍖栧璁″墠缂€鍐欏叆 `description`锛屾牸寮忥細
  - `[override][skill_gap,worker_overload] 寮哄埗鍘熷洜鏂囨湰`
  - 鑻ュ悓鏃跺～鍐欐櫘閫氬娉紝鏅€氬娉ㄤ細鎹㈣杩藉姞鍦ㄥ墠缂€鍚庛€?

### 13) 璋冨害鍛樼粓姝㈠伐鍗?

```http
PATCH /api/dispatcher/work-orders/{work_order_id}/terminate
```

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| reason | string | 鏄?| 缁堟鍘熷洜锛岄暱搴?1~500 |

### 14) 璋冨害鍛樻墜鍔ㄦ爣璁伴樁娈靛畬鎴?

```http
POST /api/dispatcher/orders/{order_id}/stages/{stage_id}/complete
```

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| remark | string | 鏄?| 鎵嬪姩瀹屾垚鍘熷洜锛岄暱搴?1~1000 |

**璇存槑锛?*
- 杩斿洖鏈€鏂拌鍗曡鎯呭璞°€?

### 15) 鎴戠殑璁㈠崟鍒楄〃鍙傛暟琛ュ厖锛堝彉鏇达級

```http
GET /api/dispatcher/my-orders?search=鍏抽敭璇?status=completed
```

**鏂板鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| status | string | - | `in_progress \| completed \| cancelled` |

**璇存槑锛?*
- 鐢ㄤ簬璋冨害鍛樷€滄垜鐨勮鍗?/ 宸插畬鎴愯鍗曗€濆垎瑙嗗浘鍔犺浇銆?

### 16) 璋冨害鍛樺伐鍗曚腑蹇冨垪琛紙鏂板锛?

```http
GET /api/dispatcher/work-orders?search=鍏抽敭璇?status=in_progress&sort_by=updated_at&sort_order=desc
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| search | string | - | 鎸夊伐鍗旾D / 璁㈠崟鍙?/ 瀹㈡埛鍚?/ 宸ヤ汉鍚嶆ā绯婃悳绱紙涓嶅尮閰嶅伐鍗曞娉級 |
| status | string | - | `pending \| in_progress \| completed \| terminated` |
| sort_by | string | updated_at | `created_at \| updated_at \| deadline` |
| sort_order | string | desc | `asc \| desc` |

**璇存槑锛?*
- 浠呰繑鍥炲綋鍓嶇櫥褰曡皟搴﹀憳鏈汉鍦ㄦ墍灞炰粨搴撲笅鍒涘缓/绠＄悊鐨勫伐鍗曘€?
- 杩斿洖缁撴瀯锛歚{ items: DispatcherOrderWorkOrderResponse[], total: number }`銆?
- `DispatcherOrderWorkOrderResponse` 棰濆杩斿洖锛?
  - `order_no`锛氳鍗曞彿
  - `customer_name`锛氬鎴峰悕绉?

---

## 绠＄悊鍛樺伐鍗曞彧璇绘€昏鎺ュ彛锛堟柊澧烇級

```http
GET /api/admin/work-orders
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| page | int | 1 | 褰撳墠椤电爜锛屾渶灏?1 |
| page_size | int | 10 | 姣忛〉鏉℃暟锛?~100 |
| search | string | - | 鎸夎鍗曞彿/宸ヤ汉鍚?璋冨害鍛樺悕/浠撳簱鍚嶆悳绱?|
| status | string | - | `pending \| in_progress \| completed \| terminated` |
| stage_type | string | - | `picking \| staging \| shipping` |
| priority | string | - | `high \| medium \| low` |
| warehouse_id | int | - | 鎸変粨搴撹繃婊?|
| worker_id | int | - | 鎸夊伐浜鸿繃婊?|
| dispatcher_id | int | - | 鎸夎皟搴﹀憳杩囨护 |

**鎴愬姛鍝嶅簲绀轰緥锛?*

```json
{
  "items": [
    {
      "id": 3001,
      "order_id": 1008,
      "order_no": "ORD-20260321-0012",
      "stage_id": 56,
      "stage_type": "picking",
      "warehouse_id": 1,
      "warehouse_name": "鍖椾含涓績鍛ㄨ浆浠?,
      "worker_id": 23,
      "worker_name": "worker_li",
      "dispatcher_id": 8,
      "dispatcher_name": "disp_chen",
      "status": "in_progress",
      "priority": "high",
      "source": "manual",
      "description": "鍏堝鐞嗘槗纰庡搧",
      "deadline": null,
      "started_at": "2026-03-21T12:05:00",
      "completed_at": null,
      "terminated_at": null,
      "created_at": "2026-03-21T12:00:00",
      "updated_at": "2026-03-21T12:05:00"
    }
  ],
  "total": 1
}
```

---

## 绠＄悊鍛樿鍗曠敓鍛藉懆鏈熸帴鍙ｈˉ鍏咃紙鏂板锛?

```http
PATCH /api/admin/orders/{order_id}/pending
POST  /api/admin/orders/{order_id}/cancel
POST  /api/admin/orders/{order_id}/reopen
```

### 1) 缂栬緫寰呮帴鍗曡鍗?

浠呭厑璁?`pending_acceptance` 璁㈠崟銆?

### 2) 鍙栨秷寰呮帴鍗曡鍗?

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| cancellation_reason | string | 鏄?| 鍙栨秷鍘熷洜锛?~500 |

### 3) 閲嶅紑宸插彇娑堣鍗?

浼氬熀浜庡師宸插彇娑堣鍗曟槑缁嗗垱寤轰竴寮犳柊鐨勫緟鎺ュ崟璁㈠崟銆?

---

## 宸ヤ汉妯″潡鎺ュ彛锛圵orker锛岃ˉ鍏級

> 璁よ瘉瑕佹眰锛氫互涓嬫帴鍙ｅ潎闇€ `Authorization: Bearer <token>`锛屼笖褰撳墠鐢ㄦ埛瑙掕壊蹇呴』涓?`worker`銆?

```http
GET   /api/worker/work-orders
GET   /api/worker/work-orders/{work_order_id}
PATCH /api/worker/work-orders/{work_order_id}/start
PATCH /api/worker/work-orders/{work_order_id}/complete
```

### 1) 鎴戠殑宸ュ崟鍒楄〃

```http
GET /api/worker/work-orders?status=in_progress
```

**鏌ヨ鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 榛樿鍊?| 璇存槑 |
|------|------|--------|------|
| status | string | - | `pending \| in_progress \| completed \| terminated` |

**璇存槑锛?*
- 浠呰繑鍥炲綋鍓嶇櫥褰曞伐浜虹殑宸ュ崟锛堝悗绔寜 `worker_id = current_user.id` 寮虹害鏉燂級銆?
- 褰撳伐鍗曠敱璋冨害鍛橀闄╂斁琛屽垱寤烘椂锛宍description` 鍙兘鍖呭惈缁撴瀯鍖栧墠缂€锛?
  - `[override][risk_codes] override_reason`銆?
  鍓嶇搴斿湪宸ュ崟璇︽儏涓睍绀鸿缁撴瀯鍖栦俊鎭紙椋庨櫓绫诲瀷銆佹斁琛屽師鍥狅級浠ュ強澶囨敞姝ｆ枃銆?

### 2) 宸ュ崟璇︽儏

```http
GET /api/worker/work-orders/{work_order_id}
```

**璺緞鍙傛暟锛?*

| 鍙傛暟 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| work_order_id | int | 宸ュ崟 ID |

**鎴愬姛鍝嶅簲锛堣妭閫夛級锛?*

```json
{
  "id": 1201,
  "order_id": 3001,
  "order_no": "ORD-20260322-0001",
  "stage_id": 8101,
  "stage_type": "picking",
  "status": "in_progress",
  "priority": "high",
  "description": "[override][skill_gap] 绱ф€ヨˉ鍗昞n浼樺厛澶勭悊 A 鍖鸿揣鏋?,
  "source": "manual",
  "worker_stage_skill": 4,
  "stage_required_skill_min": 2,
  "stage_required_skill_max": 6,
  "order_items": [
    {
      "product_id": 501,
      "product_sku": "SKU-10001",
      "product_name": "闃查渿娉℃搏",
      "product_cover_image": "/resources/product_images/p501.png",
      "qty": 6,
      "req_skill_picking": 3,
      "req_skill_staging": 2,
      "req_skill_shipping": 1,
      "current_stage_required_skill": 3,
      "worker_stage_skill": 4,
      "is_skill_matched": true
    },
    {
      "product_id": 502,
      "product_sku": "SKU-10002",
      "product_name": "绮惧瘑鐜荤拑浠?,
      "product_cover_image": "/resources/product_images/p502.png",
      "qty": 2,
      "req_skill_picking": 6,
      "req_skill_staging": 5,
      "req_skill_shipping": 4,
      "current_stage_required_skill": 6,
      "worker_stage_skill": 4,
      "is_skill_matched": false
    }
  ]
}
```

**瀛楁璇存槑锛堟湰娆℃柊澧烇級锛?*

| 瀛楁 | 绫诲瀷 | 璇存槑 |
|------|------|------|
| worker_stage_skill | int | 褰撳墠宸ュ崟闃舵涓嬶紝宸ヤ汉鑷韩鎶€鑳藉€?|
| stage_required_skill_min | int | 褰撳墠宸ュ崟闃舵涓嬶紝璁㈠崟鍟嗗搧鎶€鑳借姹傛渶灏忓€?|
| stage_required_skill_max | int | 褰撳墠宸ュ崟闃舵涓嬶紝璁㈠崟鍟嗗搧鎶€鑳借姹傛渶澶у€?|
| order_items | array | 璁㈠崟鍟嗗搧鏄庣粏锛堝惈鎶€鑳藉尮閰嶇粨鏋滐級 |

`order_items` 瀛愬瓧娈碉細
- `product_id` / `product_sku` / `product_name` / `product_cover_image`
- `qty`锛氬晢鍝佹暟閲?
- `req_skill_picking` / `req_skill_staging` / `req_skill_shipping`锛氬晢鍝佷笁闃舵鎶€鑳借姹?
- `current_stage_required_skill`锛氬綋鍓嶅伐鍗曢樁娈靛搴旂殑鎶€鑳借姹傚€?
- `worker_stage_skill`锛氬綋鍓嶅伐鍗曢樁娈典笅鐨勫伐浜烘妧鑳藉€?
- `is_skill_matched`锛歚worker_stage_skill >= current_stage_required_skill` 鏃朵负 `true`

**璇存槑锛?*
- 浠呭厑璁告煡鐪嬪綋鍓嶇櫥褰曞伐浜鸿嚜宸辫鍒嗛厤鐨勫伐鍗曡鎯咃紝鍚﹀垯杩斿洖 `404`銆?
- `description` 鑻ュ寘鍚闄╂斁琛岀粨鏋勫寲鍓嶇紑锛屽墠绔簲鍚屾椂灞曠ず鈥滈闄╃被鍨?鏀捐鍘熷洜/澶囨敞姝ｆ枃鈥濄€?

### 3) 寮€濮嬪伐鍗?

```http
PATCH /api/worker/work-orders/{work_order_id}/start
```

**璇存槑锛?*
- 浠呭厑璁哥姸鎬佷负 `pending` 鐨勫伐鍗曞紑濮嬨€?
- 鑻ヨ宸ュ崟鎵€灞為樁娈垫湁鍓嶇疆闃舵锛屽墠缃樁娈甸渶宸插畬鎴愩€?

### 4) 瀹屾垚宸ュ崟

```http
PATCH /api/worker/work-orders/{work_order_id}/complete
```

**璇锋眰浣?(JSON)锛?*

| 瀛楁 | 绫诲瀷 | 蹇呭～ | 璇存槑 |
|------|------|------|------|
| note | object | 鍚?| 鍙€夊伐鍗曞娉ㄥ璞?|

`note` 瀛愬瓧娈碉細
- `note_type`: `normal \| damaged \| qty_mismatch \| other`
- `content`: string锛岄暱搴?1~2000

**璇存槑锛?*
- 鎿嶄綔浜哄繀椤绘槸璇ュ伐鍗曡鍒嗛厤宸ヤ汉锛屽惁鍒欒繑鍥?`403`銆?

## Order-Level Agent Dispatch (Updated)

### Suggest Work Orders by Agent

```http
POST /api/dispatcher/agent/orders/{order_id}/work-orders/suggest
```

Request body:

```json
{
  "intent": "Optional dispatcher intent",
  "search_worker": "Optional worker keyword"
}
```

Response body:

```json
{
  "order_id": 1001,
  "stages": [
    {
      "stage_id": 301,
      "stage_type": "picking",
      "assignable": true,
      "reason": null,
      "required_skill_min": 3,
      "required_skill_max": 7,
      "has_risk": false,
      "risks": [],
      "worker": {
        "worker_id": 17,
        "worker_name": "worker_a",
        "worker_skill": 8,
        "pending_count": 1,
        "in_progress_count": 0,
        "active_work_order_count": 1,
        "active_work_order_limit": 5
      },
      "score": {
        "speedup": 2.65,
        "load": 0.5,
        "load_penalty": 0.8333,
        "final_score": 68.75
      },
      "priority": "high",
      "suggested_description": "..."
    },
    {
      "stage_id": 302,
      "stage_type": "staging",
      "assignable": false,
      "reason": "No worker can satisfy minimum stage skill requirement",
      "required_skill_min": 0,
      "required_skill_max": 0,
      "has_risk": false,
      "risks": [],
      "worker": null,
      "score": null,
      "priority": null,
      "suggested_description": null
    }
  ]
}
```

Notes:
- This API always returns `200` for business-level "unassignable" stages.
- Ranking uses worker-score: `finalScore DESC`, then `worker_id ASC`.
- Skill gate remains hard: `worker_skill < required_skill_min` is excluded.

### Confirm Work Orders by Agent

```http
POST /api/dispatcher/agent/orders/{order_id}/work-orders/confirm
```

Request body:

```json
{
  "intent": "Optional dispatcher intent",
  "stage_overrides": [
    { "stage_id": 301, "override_reason": "approved by dispatcher" }
  ]
}
```

Response body:

```json
{
  "order_id": 1001,
  "created_work_orders": [
    {
      "id": 9001,
      "order_id": 1001,
      "stage_id": 301,
      "stage_type": "picking",
      "worker_id": 17,
      "worker_name": "worker_a",
      "dispatcher_id": 9,
      "warehouse_id": 2,
      "status": "pending",
      "priority": "high",
      "deadline": null,
      "description": "...",
      "source": "agent",
      "started_at": null,
      "completed_at": null,
      "terminated_at": null,
      "terminated_by": null,
      "termination_reason": null,
      "created_at": "2026-03-25T17:00:00",
      "updated_at": "2026-03-25T17:00:00"
    }
  ],
  "stages": [
    {
      "stage_id": 301,
      "stage_type": "picking",
      "status": "created",
      "reason": null,
      "has_risk": false,
      "risks": [],
      "work_order_id": 9001
    },
    {
      "stage_id": 302,
      "stage_type": "staging",
      "status": "unassignable",
      "reason": "No worker can satisfy minimum stage skill requirement",
      "has_risk": false,
      "risks": [],
      "work_order_id": null
    }
  ]
}
```

Notes:
- Confirm is atomic. If any stage creation fails, all creations roll back.
- Worker selection is locked to agent decision and cannot be submitted from frontend.
- Risk stages require stage-specific `override_reason`.
