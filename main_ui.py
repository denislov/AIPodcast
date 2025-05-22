import sys
import os
from PySide6.QtWidgets import QApplication
from app.topic_ui import TopicUI

def main():
    # 确保data目录存在
    os.makedirs("data/topic", exist_ok=True)
    
    app = QApplication(sys.argv)
    window = TopicUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()