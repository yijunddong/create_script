import os
import tkinter as tk
from tkinter import scrolledtext, ttk
import google.generativeai as genai
from datetime import datetime
import threading
from dotenv import load_dotenv

# .env 파일 경로 설정 (절대 경로 사용)
env_path = r"C:\Users\USER\OneDrive\바탕 화면\project\create_script\data\.env"


# 환경 변수 파일 직접 읽기
try:
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except Exception as e:
    print("환경 변수 파일 읽기 오류:", str(e))

# Gemini API 설정
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

genai.configure(api_key=api_key)

# 모델 설정
model = genai.GenerativeModel('gemini-2.0-flash')

class ModernChatBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Assistant")
        self.root.geometry("1000x800")
        self.root.configure(bg='#ffffff')
        
        # 스타일 설정
        self.style = ttk.Style()
        self.style.configure('Modern.TFrame', background='#ffffff')
        self.style.configure('Chat.TFrame', background='#ffffff')
        self.style.configure('Input.TFrame', background='#ffffff')
        
        # 메인 프레임
        self.main_frame = ttk.Frame(root, style='Modern.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # 헤더
        self.header_frame = ttk.Frame(self.main_frame, style='Modern.TFrame')
        self.header_frame.pack(fill=tk.X, pady=(0, 30))
        
        self.title_label = tk.Label(
            self.header_frame,
            text="AI Assistant",
            font=('Segoe UI', 32, 'bold'),
            bg='#ffffff',
            fg='#1a73e8'
        )
        self.title_label.pack()
        
        # 채팅 영역
        self.chat_frame = ttk.Frame(self.main_frame, style='Chat.TFrame')
        self.chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 30))
        
        self.chat_area = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 11),
            bg='#ffffff',
            fg='#202124',
            padx=30,
            pady=30,
            relief=tk.FLAT,
            borderwidth=0
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        # 메시지 스타일 설정
        self.chat_area.tag_configure('user', foreground='#1a73e8', justify='right', font=('Segoe UI', 11, 'bold'))
        self.chat_area.tag_configure('assistant', foreground='#34a853', justify='left', font=('Segoe UI', 11, 'bold'))
        self.chat_area.tag_configure('time', foreground='#5f6368', font=('Segoe UI', 9))
        self.chat_area.tag_configure('user_msg', background='#e8f0fe', relief=tk.FLAT, borderwidth=0, lmargin1=100, lmargin2=100, rmargin=50)
        self.chat_area.tag_configure('assistant_msg', background='#f1f3f4', relief=tk.FLAT, borderwidth=0, lmargin1=50, lmargin2=50, rmargin=100)
        
        # 입력 영역
        self.input_frame = ttk.Frame(self.main_frame, style='Input.TFrame')
        self.input_frame.pack(fill=tk.X)
        
        self.input_field = tk.Text(
            self.input_frame,
            height=3,
            font=('Segoe UI', 11),
            bg='#f1f3f4',
            fg='#202124',
            padx=20,
            pady=15,
            relief=tk.FLAT,
            borderwidth=0
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
        self.input_field.bind('<Return>', self.handle_return)
        self.input_field.bind('<Shift-Return>', lambda e: None)
        
        self.send_button = tk.Button(
            self.input_frame,
            text="전송",
            command=self.send_message,
            font=('Segoe UI', 11, 'bold'),
            bg='#1a73e8',
            fg='white',
            padx=25,
            pady=12,
            relief=tk.FLAT,
            cursor='hand2',
            activebackground='#1557b0',
            activeforeground='white'
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # 초기 메시지
        self.add_message("안녕하세요! AI Assistant입니다. 무엇을 도와드릴까요?", 'assistant')
        
        # 로딩 상태
        self.is_loading = False
        
    def handle_return(self, event):
        if not event.state & 0x1:  # Shift 키가 눌려있지 않을 때
            self.send_message()
            return 'break'
    
    def add_message(self, message, sender):
        self.chat_area.config(state=tk.NORMAL)
        
        # 시간 추가
        current_time = datetime.now().strftime("%H:%M")
        self.chat_area.insert(tk.END, f"\n[{current_time}] ", 'time')
        
        # 발신자 표시
        sender_text = "나" if sender == 'user' else "AI"
        self.chat_area.insert(tk.END, f"{sender_text}: ", sender)
        
        # 메시지 배경색 설정
        msg_tag = 'user_msg' if sender == 'user' else 'assistant_msg'
        
        # 메시지 추가
        self.chat_area.insert(tk.END, f"{message}\n", msg_tag)
        
        # 스크롤을 항상 아래로
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)
    
    def show_loading(self):
        self.is_loading = True
        self.send_button.config(state=tk.DISABLED)
        self.add_message("답변을 생성하는 중...", 'assistant')
    
    def hide_loading(self):
        self.is_loading = False
        self.send_button.config(state=tk.NORMAL)
        # 마지막 메시지(로딩 메시지) 삭제
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete("end-2l linestart", "end")
        self.chat_area.config(state=tk.DISABLED)
    
    def send_message(self):
        user_input = self.input_field.get("1.0", tk.END).strip()
        if not user_input or self.is_loading:
            return
        
        # 입력 필드 초기화
        self.input_field.delete("1.0", tk.END)
        
        # 사용자 메시지 표시
        self.add_message(user_input, 'user')
        
        # 로딩 표시
        self.show_loading()
        
        # 별도 스레드에서 API 호출
        threading.Thread(target=self.get_ai_response, args=(user_input,), daemon=True).start()
    
    def get_ai_response(self, user_input):
        try:
            response = model.generate_content(user_input)
            self.root.after(0, self.hide_loading)
            self.root.after(0, lambda: self.add_message(response.text, 'assistant'))
        except Exception as e:
            self.root.after(0, self.hide_loading)
            self.root.after(0, lambda: self.add_message(f"오류가 발생했습니다: {str(e)}", 'assistant'))

def main():
    root = tk.Tk()
    app = ModernChatBotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
