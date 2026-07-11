ถ้าให้ผมออกแบบ **กลไกแยก stage ที่ simple ที่สุดแต่ยังน่าเชื่อถือ** ผมจะ **ไม่เริ่มจาก pyro** ครับ
ผมจะใช้แบบ:

> **Spring-loaded mechanical separation + simple latch/pin release**

เพราะมันผลิตง่าย, ทดสอบซ้ำได้, ไม่ shock avionics หนัก, และไม่ต้องยุ่งกับระเบิด/pyro hardware ตั้งแต่แรก

## Concept ที่ผมเลือก

โครงสร้างประมาณนี้:

```text
        Second Stage
   ┌─────────────────┐
   │                 │
   │   Upper motor   │
   │                 │
   └───────┬─────────┘
           │ aft skirt / coupler
        ┌──┴──┐
        │     │  ← male coupler
 ┌──────┴─────┴──────┐
 │   Interstage tube │
 │                   │
 │  ↑ spring  spring ↑
 │                   │
 │   latch / pull pin│
 └─────────┬─────────┘
           │
       First Stage
```

## หลักการทำงาน

ตอนประกอบ:

1. **stage 2 เสียบอยู่ใน interstage ของ stage 1**
2. มี **shoulder / thrust ring** รับแรงกดหลักตอน first stage thrusting
   จุดนี้สำคัญมาก อย่าให้ latch หรือ pin ตัวเล็กรับ thrust หลัก
3. มี **compression spring** 3 ตัวรอบวง หรือ 1 ตัวตรงกลาง คอยดัน stage 2 ออกจาก stage 1
4. มี **latch pin / retaining pin** ล็อกไว้ไม่ให้ spring ดันแยกก่อนเวลา
5. เมื่อ first stage burnout → flight computer สั่ง release pin
6. spring ดันให้ stage 2 แยกออก
7. ตรวจว่าแยกแล้วด้วย limit switch / magnetic switch / break-wire
8. ค่อยอนุญาตให้ stage 2 ignition

สรุป flow:

```text
First stage burnout
      ↓
wait / verify condition
      ↓
release latch pin
      ↓
spring pushes stages apart
      ↓
separation confirmed
      ↓
second stage ignition
```

## ชิ้นส่วนหลักที่ผมจะใช้

### 1. Interstage sleeve

เป็นท่อครอบระหว่าง stage 1 กับ stage 2
หน้าที่คือ:

* จัด alignment
* กัน stage 2 โยก
* รับ bending บางส่วน
* เป็น guide ตอนแยก

ให้มี clearance พอดี ไม่แน่นจน friction สูง แต่ไม่หลวมจน stage 2 โยก

---

### 2. Thrust shoulder / load ring

นี่คือจุดที่ผมให้ความสำคัญที่สุด

ตอน first stage thrusting แรงจาก stage 1 ต้องส่งไปดัน stage 2 ผ่าน **บ่ารับแรง** ไม่ใช่ผ่าน pin เล็ก ๆ

```text
Stage 2 aft skirt
     │
     ▼
 [ thrust shoulder ]
     ▲
     │
Interstage / Stage 1
```

ถ้าออกแบบผิดให้ latch pin รับ axial load หลัก พอ vibration + thrust มา pin อาจโก่ง ติด หรือปลดไม่ออก
อันนี้คือ recipe สำหรับ “จรวดรวมร่างถาวร” แบบไม่สมัครใจ

---

### 3. Spring pusher

เลือกได้สองแบบ:

#### แบบง่ายสุด: central spring

มี spring ตัวเดียวตรงกลาง ดัน stage 2 ออก

ข้อดี: ง่าย, ชิ้นส่วนน้อย
ข้อเสีย: ถ้าแนวแรงไม่ตรงศูนย์ อาจทำให้ stage 2 pitch/yaw ตอนแยก

#### แบบที่ผมชอบกว่า: 3 springs รอบวง

วาง 120° รอบแกนลำตัว

ข้อดี:

* แรงสมมาตร
* ลด moment ตอนแยก
* ถ้าตัวใดตัวหนึ่งแรงต่างนิดหน่อย ยังพอรับได้

```text
top view

       spring
          ▲
          │
 spring ◄ ○ ► spring
```

สำหรับจรวดจริงจัง ผมเลือก **3 springs รอบวง** ครับ ยัง simple แต่ปลอดภัยกว่า central spring เยอะ

---

### 4. Retaining pin / latch

ใช้ pin หนึ่งตัวล็อก ring หรือ tab ไว้
เมื่อถึงเวลา actuator ดึง pin ออก

ตัวปลดล็อกที่ simple มี 2 ทาง:

#### Option A: micro-servo pull pin

เหมาะกับ prototype เพราะ reset ได้ง่าย

ข้อดี:

* ทดสอบซ้ำง่าย
* ไม่ใช้ pyro
* debug ง่าย

ข้อเสีย:

* servo แพ้ vibration/heat/ฝุ่นได้
* ต้องมีไฟเลี้ยงและ mechanical travel ชัดเจน

#### Option B: burn-wire release

ใช้ลวดร้อนตัดเชือก/loop ที่รั้ง pin หรือ latch ไว้

ข้อดี:

* ชิ้นส่วนน้อยมาก
* ไม่มี motor gear
* เบา

ข้อเสีย:

* one-time use
* ต้องทดสอบ timing และความน่าเชื่อถือดี ๆ

ถ้าทำ prototype ภาคสนาม ผมเริ่มด้วย **servo pull-pin** ก่อน
ถ้าจะลดชิ้นส่วนสำหรับ flight article ค่อยพิจารณา **burn-wire release**

---

### 5. Shear pins / nylon screws

ใช้เป็นตัวกัน stage หลุดระหว่าง handling, vibration, หรือ aerodynamic load

แต่ผมจะไม่ให้มันเป็นตัวรับโหลดหลัก
มันควรทำหน้าที่เหมือน “ตัวกันหลุด/ตัวกำหนดแรงแยกขั้นต่ำ” มากกว่า

ใช้ 3 ตัวรอบวงก็พอสำหรับ layout ง่าย ๆ

---

### 6. Separation confirmation

ผมจะใส่ sensor ง่าย ๆ อย่างน้อยหนึ่งตัว เช่น:

* break-wire
* microswitch
* magnetic reed switch
* Hall sensor + magnet

หลักคือ stage 2 ignition ต้องมี condition:

```text
burnout detected
AND release command sent
AND separation confirmed
AND attitude acceptable
```

ถ้าไม่มี separation confirmed → **ห้ามจุด stage 2**

ตรงนี้สำคัญมาก เพราะถ้า stage 2 ติดตอนยังไม่แยกดี มันจะกลายเป็น hot-staging แบบไม่ได้ตั้งใจ ซึ่ง interstage อาจไม่ได้ออกแบบรับ thermal/pressure load

---

## Design ที่ผมจะเลือกจริง

ผมจะใช้ configuration นี้:

```text
Simple reliable separation mechanism

- Interstage tube เป็น guide
- Thrust shoulder รับ axial load
- 3 compression springs รอบวง
- 1 pull-pin latch กลาง/ด้านข้าง
- 3 nylon shear pins รอบวง
- break-wire confirm separation
- vent holes กัน pressure lock
```

ภาพรวม:

```text
        SECOND STAGE
     ┌────────────────┐
     │                │
     └──────┬─────────┘
            │
       ┌────┴────┐
       │ coupler │
       └─┬────┬──┘
         │    │
    spring    spring
         │    │
 ┌───────┴────┴────────┐
 │     interstage       │
 │                      │
 │   latch pin / lock   │
 │                      │
 └─────────┬────────────┘
           │
       FIRST STAGE
```

## สิ่งที่ผมจะหลีกเลี่ยงใน design แรก

* pyro bolt
* explosive separation charge
* hot staging
* clamp band แบบซับซ้อน
* mechanism หลาย latch หลายจุด
* latch ที่ต้องปลดพร้อมกันหลายตัว
* ให้สายไฟเป็นตัวรั้ง stage
* fit แน่นเกินจนเสี่ยงติดตอนแยก

เพราะของพวกนี้ไม่ได้ “simple” จริงในระบบจรวด มัน simple บนกระดาษ แต่ตอน test จะเริ่มมีผี: shock, misalignment, thermal, vibration, binding, cable snag

## จุดสำคัญที่สุด

ถ้าให้เลือกหนึ่งประโยค:

> **ให้ thrust load วิ่งผ่านโครงสร้างแข็งแรง ส่วน latch มีหน้าที่แค่ “สั่งปล่อย” ไม่ใช่ “แบกจรวด”**

อันนี้คือหัวใจของกลไก separation แบบง่ายและดีครับ.

ถ้าเป็นงานของคุณ ผมจะเริ่มจาก **non-pyro spring separation** ก่อน แล้วทำ mock-up ทดสอบแยกบนโต๊ะให้ผ่าน 20–50 รอบก่อน ค่อยไปคิดเรื่อง flight version.
