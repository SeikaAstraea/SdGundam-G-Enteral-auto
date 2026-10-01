import cv2
import numpy as np
import time
import subprocess
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

class GundamAutoBot:
    def __init__(self, adb_path="adb", adb_device="127.0.0.1:7555"):
        self.adb_path = adb_path
        self.adb_device = adb_device
        self.connect_adb()
        self.last_action = None 
        
        self.templates = {
            "tap_to_next": self.load_template("tpl_tap_to_next.png"),
            "next_btn": self.load_template("tpl_next.png"),
            "retry_btn": self.load_template("tpl_retry.png"),
            "stamina_empty": self.load_template("tpl_stamina.png")
        }

    def connect_adb(self):
        print(f"正在连接模拟器 {self.adb_device}...")
        subprocess.run([self.adb_path, "connect", self.adb_device], capture_output=True)

    def load_template(self, filename):
        if not os.path.exists(filename):
            print(f"⚠️ 警告: 找不到 {filename}")
            return None
        # 恢复正常的灰度识别，去除了容易导致轮廓误判的二值化
        return cv2.imread(filename, cv2.IMREAD_GRAYSCALE)

    def get_adb_screen(self):
        cmd = [self.adb_path, "-s", self.adb_device, "exec-out", "screencap", "-p"]
        process = subprocess.run(cmd, capture_output=True)
        if process.returncode != 0 or len(process.stdout) == 0:
            return None
        screen_array = np.frombuffer(process.stdout, dtype=np.uint8)
        img = cv2.imdecode(screen_array, cv2.IMREAD_COLOR)
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def adb_tap(self, x, y):
        cmd = [self.adb_path, "-s", self.adb_device, "shell", "input", "swipe", str(x), str(y), str(x), str(y), "50"]
        subprocess.run(cmd, capture_output=True)

    def find_and_tap(self, screen_gray, template, name="按钮", threshold=0.55, roi=None):
        if template is None:
            return False
            
        h_screen, w_screen = screen_gray.shape
        offset_x, offset_y = 0, 0
        search_img = screen_gray

        if roi is not None:
            x1, y1 = int(roi[0] * w_screen), int(roi[1] * h_screen)
            x2, y2 = int(roi[2] * w_screen), int(roi[3] * h_screen)
            search_img = screen_gray[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1

        result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 💡 【核心黑科技：防抖确认机制】
        if max_val >= threshold:
            # 第一次觉得像，不着急点，等 0.5 秒看看它还在不在
            time.sleep(0.5) 
            confirm_screen = self.get_adb_screen()
            if confirm_screen is None:
                return False
                
            # 再切同一块区域看一次
            confirm_search_img = confirm_screen[y1:y2, x1:x2] if roi else confirm_screen
            res_confirm = cv2.matchTemplate(confirm_search_img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val_confirm, _, _ = cv2.minMaxLoc(res_confirm)
            
            # 如果 0.5 秒后相似度还在阈值之上，说明是真 UI！
            if max_val_confirm >= threshold:
                h, w = template.shape
                center_x = offset_x + max_loc[0] + w // 2
                center_y = offset_y + max_loc[1] + h // 2
                self.adb_tap(center_x, center_y)
                return True
            else:
                # 如果 0.5 秒后形状变了，说明是爆炸特效
                print(f"[{time.strftime('%H:%M:%S')}] 👻 成功拦截一次战斗特效对 [{name}] 的伪装！")
                return False
                
        return False

    def run(self):
        print("====== SD高达G世纪永恒 智能防抖脚本已启动 ======")
        try:
            while True:
                screen = self.get_adb_screen()
                if screen is None:
                    time.sleep(1)
                    continue

                # 1. 结算次へ判定 (阈值 0.55 + 0.5秒防抖)
                if self.find_and_tap(screen, self.templates["next_btn"], "次へ", threshold=0.55, roi=(0.5, 0.7, 1.0, 1.0)):
                    if self.last_action != "next":
                        print(f"[{time.strftime('%H:%M:%S')}] ➡️ 识别到 [次へ] 结算按钮。")
                        self.last_action = "next"
                    time.sleep(2)

                # 2. 再出击判定与【体力耗尽拦截】
                elif self.find_and_tap(screen, self.templates["retry_btn"], "再出击", threshold=0.55, roi=(0.5, 0.7, 1.0, 1.0)):
                    if self.last_action != "retry":
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ 识别到 [再出击] 按钮，尝试进入下一局...")
                        self.last_action = "retry"
                    
                    # 💡 核心修改：点完再出击后，不要立刻盲点！先等 3 秒让弹窗飞一会儿
                    time.sleep(3)
                    check_screen = self.get_adb_screen()
                    
                    if check_screen is not None and self.templates["stamina_empty"] is not None:
                        # 纯视觉检测 AP回复 弹窗，不执行点击
                        res = cv2.matchTemplate(check_screen, self.templates["stamina_empty"], cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        
                        if max_val >= 0.50:
                            print(f"[{time.strftime('%H:%M:%S')}] 🛑 侦测到 [AP回復] 弹窗，体力已耗尽，脚本安全停止！")
                            break # 直接跳出 while 循环，结束整个脚本
                    
                    # 如果刚才没看到弹窗，说明成功出击，放心开始盲点
                    print(f"[{time.strftime('%H:%M:%S')}] ⏩ 体力充足，触发盲点：连续 10 秒跳过过场动画...")
                    h, w = screen.shape
                    safe_x, safe_y = w // 2, int(h * 0.8) 
                    
                    for i in range(10):
                        self.adb_tap(safe_x, safe_y)
                        time.sleep(1)
                        
                    print(f"[{time.strftime('%H:%M:%S')}] 💤 动画结束，脚本进入 30 秒深度休眠，无视一切战斗特效...")
                    time.sleep(30)
                
                else:
                    self.last_action = None

                time.sleep(1.5)

        except KeyboardInterrupt:
            print("\n[紧急停止] 收到手动退出指令，脚本中止。")

if __name__ == "__main__":
    # 注意把路径改回你的 adb 路径
    mumu_adb_path = r"D:\MuMuPlayer\nx_device\12.0\shell\adb.exe" 
    bot = GundamAutoBot(adb_path=mumu_adb_path, adb_device="127.0.0.1:7555") 
    bot.run()