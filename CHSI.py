import os, time, pandas as pd, re, traceback, sys, subprocess, pyperclip, pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CERT_BOX_COORDS, NAME_BOX_COORDS, CAPTCHA_BOX_COORDS = (661, 580), (666, 630), (673, 700)
RIGHT_CLICK_COORDS, LENS_MENU_COORDS, LENS_FLOAT_COPY_COORDS = (768, 600), (920, 811), (546, 678)
CLOSE_LENS_PANEL_COORDS = (1878, 170)
URL = "https://www.chsi.com.cn/xlcx/lscx/query.do"
SUBMIT_BTN_XPATH = "//*[@id='leftH']/div[2]/div/div/form[2]/div[4]/div/button"
AGREE_XPATH = "//*[@id='leftH']/div[2]/div/div/form[2]/div[4]/div/div[1]/label"

def auto_launch_chrome():
    paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")]
    for p in paths:
        if os.path.exists(p):
            subprocess.Popen([p, "--remote-debugging-port=9222", "--user-data-dir=C:\\SeleniumChromeProfile"])
            time.sleep(3); return True
    return False

def save_result_screenshot(driver, name, cert_num):
    try:
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHSI"); os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, f"{re.sub(r'[\\/*?:\"<>|]', '_', name)}_{cert_num}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        driver.execute_script("window.scrollTo(0, 0);"); time.sleep(0.5)
        driver.save_screenshot(filepath); print(f"   📸 Screenshot perfectly saved -> {filepath}")
    except Exception as e: print(f"   ⚠️ Could not save screenshot: {e}")

def close_lens_panel(): pyautogui.click(*CLOSE_LENS_PANEL_COORDS); time.sleep(0.5)
def paste_text(t): pyperclip.copy(t); time.sleep(0.1); pyautogui.hotkey('ctrl', 'v'); time.sleep(0.1)

def reload_and_refill(driver, cert_num, name):
    close_lens_panel(); driver.get(URL); wait = WebDriverWait(driver, 15)
    try: wait.until(EC.presence_of_element_located((By.XPATH, SUBMIT_BTN_XPATH)))
    except: pass
    time.sleep(1)
    pyautogui.click(*CERT_BOX_COORDS); time.sleep(0.2); pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); paste_text(cert_num)
    pyautogui.click(*NAME_BOX_COORDS); time.sleep(0.2); pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); paste_text(name)
    pyautogui.click(*CAPTCHA_BOX_COORDS); time.sleep(0.8)
    return wait

def captcha_was_accepted(driver):
    if not driver.find_elements(By.XPATH, SUBMIT_BTN_XPATH): return True
    return False

def process_captcha_text(raw_text):
    raw_text = raw_text.strip(); print(f"   -> Lens Extracted: '{raw_text}'")
    if not raw_text: return None
    if any(op in raw_text for op in ['+', '-', '÷', '=']) or re.search(r'\d+\s*[xX]\s*\d+', raw_text):
        try:
            ms = re.sub(r'[^0-9\+\-\*\/]', '', raw_text.replace('O','0').replace('o','0').replace('x','*').replace('X','*').replace('÷','/')).strip('+-*/')
            ans = str(eval(ms)); print(f"   -> Math Solved: {ms} = {ans}"); return ans
        except: return None
    else:
        ct = re.sub(r'[^a-zA-Z0-9]', '', raw_text); print(f"   -> Alphanumeric Cleaned: '{ct}'")
        return ct if len(ct) >= 4 else None

print("--- Starting Automation Initialization ---")
excel_file = "Candidate Data.xlsx"
if not os.path.exists(excel_file): sys.exit(1)
df = pd.read_excel(excel_file)
auto_launch_chrome()

driver = None
while not driver:
    try: opts = webdriver.ChromeOptions(); opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222"); driver = webdriver.Chrome(options=opts)
    except: time.sleep(5)
driver.maximize_window()

try:
    for idx, row in df.iterrows():
        cert_num, name = str(row['证书编号']).strip(), str(row['姓名']).strip()
        print(f"\nRow {idx+1}: {name} - {cert_num}")
        driver.get(URL); wait = WebDriverWait(driver, 15)
        try: wait.until(EC.presence_of_element_located((By.XPATH, SUBMIT_BTN_XPATH)))
        except: continue
        time.sleep(1)
        
        pyautogui.click(*CERT_BOX_COORDS); time.sleep(0.2); pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); paste_text(cert_num)
        pyautogui.click(*NAME_BOX_COORDS); time.sleep(0.2); pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); paste_text(name)
        pyautogui.click(*CAPTCHA_BOX_COORDS); time.sleep(0.8)
        
        captcha_correct, retry_count = False, 0
        while not captcha_correct and retry_count < 15:
            retry_count += 1
            print(f"   [Attempt {retry_count}/15] Reading CAPTCHA...")
            pyautogui.rightClick(*RIGHT_CLICK_COORDS); time.sleep(0.5)
            pyautogui.click(*LENS_MENU_COORDS); time.sleep(6) # 6 seconds for math safety
            pyperclip.copy(""); pyautogui.click(*LENS_FLOAT_COPY_COORDS); time.sleep(1)
            pyautogui.press('esc'); time.sleep(0.2); close_lens_panel()
            
            ans = process_captcha_text(pyperclip.paste())
            if not ans: wait = reload_and_refill(driver, cert_num, name); continue
            
            pyautogui.click(*CAPTCHA_BOX_COORDS); time.sleep(0.2); pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); paste_text(ans)
            try: wait.until(EC.element_to_be_clickable((By.XPATH, AGREE_XPATH))).click()
            except: pass
            wait.until(EC.element_to_be_clickable((By.XPATH, SUBMIT_BTN_XPATH))).click(); time.sleep(1.5)
            
            if captcha_was_accepted(driver): captcha_correct = True
            else: wait = reload_and_refill(driver, cert_num, name)
            
        if not captcha_correct: time.sleep(10); continue

        try:
            try: driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '手机验证')]")))); time.sleep(1)
            except: pass
            phone_f = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, '手机') or contains(@placeholder, '大陆')]")))
            phone_f.clear(); phone_f.send_keys("19854797648")
            driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '免费获取')]"))))
            
            print("\n🛑 Enter OTP on website and click Query.")
            print("   (Do NOT click this black window! Script is watching automatically...)")
            
            # --- AUTO-DETECT RESULT PAGE (Waits up to 5 minutes) ---
            wait_time = 0
            while "出生日期" not in driver.page_source and "未找到学历信息" not in driver.page_source and wait_time < 300:
                time.sleep(1); wait_time += 1
                
            if wait_time < 300:
                if "出生日期" in driver.page_source: print("   -> ✅ Record Found! Saving screenshot...")
                else: print("   -> ⚠️ 'No Record Found' page detected! Saving screenshot...")
                time.sleep(1.5); save_result_screenshot(driver, name, cert_num)
            else:
                print("   -> ❌ Timed out waiting for OTP. Skipping...")
            # --------------------------------------------------------
            
        except Exception as e: print(f"   -> 🚨 Mobile verification error: {e}")
except Exception: traceback.print_exc()
finally: input("\nFinished. Press ENTER to close...")
