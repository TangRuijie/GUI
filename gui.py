import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import sqlite3
import threading

class MedicalDataAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("医疗数据标注工具")
        self.root.geometry("900x800")
        
        # 数据库相关
        self.db_path = "medical_data.db"
        self.current_index = 0
        self.filtered_ids = []
        self.all_diseases = []
        self.selected_diseases = []
        self.current_selected_disease = tk.StringVar(value="未选择")
        
        # 初始化数据库和UI
        self.init_database()
        self.init_ui()
        
        # 加载数据
        self.load_data()
        
    def init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建病例数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                description TEXT,
                diagnosis TEXT,
                annotations TEXT
            )
        ''')
        
        # 创建疾病类型表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diseases (
                name TEXT PRIMARY KEY
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def init_ui(self):
        """初始化主界面"""
        # 顶部按钮区域
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10, padx=10, fill=tk.X)
        
        self.load_btn = ttk.Button(btn_frame, text="加载Excel文件", command=self.load_excel)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="选择筛选类别", command=self.select_diseases).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="批量修改类别名", command=self.batch_rename_disease).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="导出到Excel", command=self.export_excel).pack(side=tk.LEFT, padx=5)
        
        # 主内容区域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # ID显示区域 - 只读Entry，可复制
        id_frame = ttk.LabelFrame(content_frame, text="ID")
        id_frame.pack(fill=tk.X, pady=5)
        self.id_var = tk.StringVar()
        self.id_entry = ttk.Entry(id_frame, textvariable=self.id_var, state='readonly', font=('TkDefaultFont', 10))
        self.id_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # 描述显示区域 - 只读但可复制
        desc_frame = ttk.LabelFrame(content_frame, text="描述")
        desc_frame.pack(fill=tk.X, pady=5)
        self.desc_text = tk.Text(desc_frame, height=10, wrap=tk.WORD, state=tk.NORMAL,
                                 insertofftime=0, insertontime=0)  # 隐藏光标
        self.desc_text.bind("<Key>", lambda e: "break")  # 阻止键盘输入
        self.desc_text.bind("<Control-v>", lambda e: "break")  # 阻止粘贴
        self.desc_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        # 诊断显示区域 - 只读但可复制
        diag_frame = ttk.LabelFrame(content_frame, text="诊断")
        diag_frame.pack(fill=tk.X, pady=5)
        self.diag_text = tk.Text(diag_frame, height=10, wrap=tk.WORD, state=tk.NORMAL,
                                 insertofftime=0, insertontime=0)
        self.diag_text.bind("<Key>", lambda e: "break")
        self.diag_text.bind("<Control-v>", lambda e: "break")
        self.diag_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        # 标注编辑区域（高度减小）
        anno_frame = ttk.LabelFrame(content_frame, text="标注（可编辑）")
        anno_frame.pack(fill=tk.BOTH, pady=5, expand=True)
        self.anno_text = tk.Text(anno_frame, height=3, wrap=tk.WORD)  # 高度减小到3行
        self.anno_text.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        # 底部导航按钮区域
        nav_frame = ttk.Frame(content_frame)
        nav_frame.pack(pady=20)
        
        self.prev_btn = ttk.Button(nav_frame, text="上一个", command=self.previous_case)
        self.prev_btn.pack(side=tk.LEFT, padx=10)
        
        self.next_btn = ttk.Button(nav_frame, text="下一个", command=self.next_case)
        self.next_btn.pack(side=tk.LEFT, padx=10)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def batch_rename_disease(self):
        """批量修改疾病类别名称"""
        if not self.all_diseases:
            messagebox.showwarning("警告", "没有可用的疾病类别")
            return
        
        # 创建修改窗口
        rename_window = tk.Toplevel(self.root)
        rename_window.title("批量修改类别名")
        rename_window.geometry("500x200")
        rename_window.transient(self.root)
        rename_window.grab_set()
        
        # 左右分栏框架
        main_frame = ttk.Frame(rename_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左栏：选择现有类别
        left_frame = ttk.LabelFrame(main_frame, text="选择现有类别")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        selected_label = ttk.Label(left_frame, textvariable=self.current_selected_disease, 
                                   relief=tk.SUNKEN, anchor=tk.W)
        selected_label.pack(fill=tk.X, padx=5, pady=5)
        
        def select_single_disease():
            disease = self.select_single_disease_dialog()
            if disease:
                self.current_selected_disease.set(disease)
        
        ttk.Button(left_frame, text="选择...", command=select_single_disease).pack(pady=5)
        
        # 右栏：输入新类别名
        right_frame = ttk.LabelFrame(main_frame, text="新类别名")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        new_name_var = tk.StringVar()
        new_name_entry = ttk.Entry(right_frame, textvariable=new_name_var)
        new_name_entry.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(right_frame, text="注：可为空或现有类别", font=('TkDefaultFont', 8)).pack(pady=2)
        
        # 确认修改按钮
        def confirm_rename():
            old_name = self.current_selected_disease.get()
            new_name = new_name_var.get().strip()
            
            if old_name == "未选择":
                messagebox.showwarning("警告", "请先选择一个疾病类别")
                return
            
            # 确认对话框
            if new_name == "":
                message = f"确定要将 '{old_name}' 从所有病例中删除吗？"
            elif new_name == old_name:
                messagebox.showinfo("提示", "新旧名称相同，无需修改")
                return
            else:
                message = f"确定要将 '{old_name}' 重命名为 '{new_name}' 吗？"
            
            if messagebox.askyesno("确认修改", message):
                self.rename_disease(old_name, new_name)
                rename_window.destroy()
        
        ttk.Button(right_frame, text="确认修改", command=confirm_rename).pack(pady=10)
        
    def select_single_disease_dialog(self):
        """单选疾病对话框 - 返回选中的疾病名称"""
        # 创建选择窗口
        select_window = tk.Toplevel(self.root)
        select_window.title("选择单一类别")
        select_window.geometry("400x500")
        select_window.transient(self.root)
        select_window.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(select_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建Canvas和Scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        # 创建可滚动的框架
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置Canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定滚动事件
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # 鼠标滚轮支持
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 单选变量
        selected_var = tk.StringVar()
        
        # 创建单选按钮列表
        for i, disease in enumerate(self.all_diseases):
            rb = ttk.Radiobutton(scrollable_frame, text=disease, value=disease, variable=selected_var)
            rb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 按钮区域
        btn_frame = ttk.Frame(select_window)
        btn_frame.pack(pady=10)
        
        def confirm_selection():
            if not selected_var.get():
                messagebox.showwarning("警告", "请选择一个疾病类别")
                return
            select_window.destroy()
        
        ttk.Button(btn_frame, text="确定", command=confirm_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=select_window.destroy).pack(side=tk.LEFT, padx=5)
        
        # 等待窗口关闭
        self.root.wait_window(select_window)
        
        return selected_var.get() if selected_var.get() else None
        
    def rename_disease(self, old_name, new_name):
        """在数据库中批量重命名疾病（去重逻辑）"""
        def do_rename():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 获取所有包含该疾病的病例
                cursor.execute("SELECT id, annotations FROM cases WHERE annotations LIKE ?", (f"%{old_name}%",))
                cases = cursor.fetchall()
                
                updated_count = 0
                
                for case_id, annotations in cases:
                    # 分割疾病列表
                    diseases = [d.strip() for d in annotations.split('；') if d.strip()]
                    
                    # 处理替换逻辑
                    new_diseases = []
                    old_found = False
                    
                    for d in diseases:
                        if d == old_name:
                            old_found = True
                            # 如果新名称不为空且不在列表中，则添加
                            if new_name and new_name not in new_diseases:
                                new_diseases.append(new_name)
                        else:
                            if d not in new_diseases:  # 避免重复
                                new_diseases.append(d)
                    
                    # 如果有变化，更新数据库
                    if old_found:
                        new_annotations = '；'.join(new_diseases)
                        cursor.execute("UPDATE cases SET annotations = ? WHERE id = ?", (new_annotations, case_id))
                        updated_count += 1
                
                # 如果新名称是全新的，更新疾病类型表
                if new_name and new_name not in self.all_diseases:
                    cursor.execute("INSERT OR REPLACE INTO diseases (name) VALUES (?)", (new_name,))
                
                # 删除旧名称（如果没有病例再使用它）
                cursor.execute("DELETE FROM diseases WHERE name = ? AND NOT EXISTS (SELECT 1 FROM cases WHERE annotations LIKE ?)", 
                             (old_name, f"%{old_name}%"))
                
                conn.commit()
                conn.close()
                
                # 更新内存中的all_diseases列表
                self.load_data()
                
                # 清空选择
                self.current_selected_disease.set("未选择")
                
                self.root.after(0, lambda: messagebox.showinfo("成功", f"已更新 {updated_count} 条记录"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"修改失败: {str(e)}"))
        
        # 在后台线程执行
        thread = threading.Thread(target=do_rename)
        thread.daemon = True
        thread.start()
        
    def load_excel(self):
        """加载Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls")]
        )
        
        if not file_path:
            return
        
        # 创建进度条窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("解析中...")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="正在解析Excel文件...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start()
        
        # 在后台线程中解析Excel
        def parse_excel():
            try:
                df = pd.read_excel(file_path)
                required_columns = ['id', '描述', '诊断', '标注']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    raise ValueError(f"缺少必需的列: {', '.join(missing_columns)}")
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cases")
                cursor.execute("DELETE FROM diseases")
                conn.commit()
                
                all_diseases_set = set()
                
                for index, row in df.iterrows():
                    cursor.execute(
                        "INSERT INTO cases (id, description, diagnosis, annotations) VALUES (?, ?, ?, ?)",
                        (str(row['id']), str(row['描述']), str(row['诊断']), str(row['标注']))
                    )
                    
                    diseases = str(row['标注']).split('；')
                    for disease in diseases:
                        disease = disease.strip()
                        if disease:
                            all_diseases_set.add(disease)
                
                for disease in sorted(all_diseases_set):
                    cursor.execute("INSERT INTO diseases (name) VALUES (?)", (disease,))
                
                conn.commit()
                conn.close()
                
                self.root.after(0, self.load_data)
                self.root.after(0, progress_window.destroy)
                self.root.after(0, lambda: messagebox.showinfo("成功", f"已加载 {len(df)} 条记录和 {len(all_diseases_set)} 种疾病"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载失败: {str(e)}"))
                self.root.after(0, progress_window.destroy)
        
        thread = threading.Thread(target=parse_excel)
        thread.daemon = True
        thread.start()
        
    def export_excel(self):
        """导出所有数据到Excel文件"""
        file_path = filedialog.asksaveasfilename(
            title="导出Excel文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        progress_window = tk.Toplevel(self.root)
        progress_window.title("导出中...")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="正在导出数据到Excel...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start()
        
        def do_export():
            try:
                conn = sqlite3.connect(self.db_path)
                df = pd.read_sql_query("SELECT id, description, diagnosis, annotations FROM cases ORDER BY id", conn)
                conn.close()
                
                df.columns = ['id', '描述', '诊断', '标注']
                df.to_excel(file_path, index=False, engine='openpyxl')
                
                self.root.after(0, progress_window.destroy)
                self.root.after(0, lambda: messagebox.showinfo("导出成功", f"已导出 {len(df)} 条记录到\n{file_path}"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("导出失败", f"错误: {str(e)}"))
                self.root.after(0, progress_window.destroy)
        
        thread = threading.Thread(target=do_export)
        thread.daemon = True
        thread.start()
        
    def load_data(self):
        """从数据库加载数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM diseases ORDER BY name")
        self.all_diseases = [row[0] for row in cursor.fetchall()]
        
        if not self.selected_diseases:
            cursor.execute("SELECT id FROM cases ORDER BY id")
        else:
            conditions = " OR ".join(["annotations LIKE ?" for _ in self.selected_diseases])
            params = [f"%{disease}%" for disease in self.selected_diseases]
            cursor.execute(f"SELECT id FROM cases WHERE {conditions} ORDER BY id", params)
        
        self.filtered_ids = [row[0] for row in cursor.fetchall()]
        self.current_index = 0 if self.filtered_ids else -1
        
        conn.close()
        self.display_current_case()
        
    def display_current_case(self):
        """显示当前病例"""
        if self.current_index < 0 or self.current_index >= len(self.filtered_ids):
            self.id_var.set("")
            self.desc_text.config(state=tk.NORMAL)
            self.desc_text.delete(1.0, tk.END)
            self.diag_text.config(state=tk.NORMAL)
            self.diag_text.delete(1.0, tk.END)
            self.anno_text.delete(1.0, tk.END)
            self.status_var.set("无数据")
            return
        
        case_id = self.filtered_ids[self.current_index]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, description, diagnosis, annotations FROM cases WHERE id = ?", (case_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            self.id_var.set(row[0])
            
            self.desc_text.config(state=tk.NORMAL)
            self.desc_text.delete(1.0, tk.END)
            self.desc_text.insert(1.0, row[1])
            
            self.diag_text.config(state=tk.NORMAL)
            self.diag_text.delete(1.0, tk.END)
            self.diag_text.insert(1.0, row[2])
            
            self.anno_text.delete(1.0, tk.END)
            self.anno_text.insert(1.0, row[3])
            
            self.status_var.set(f"记录 {self.current_index + 1}/{len(self.filtered_ids)}")
        
    def save_current_annotation(self):
        """保存当前标注"""
        if self.current_index < 0 or self.current_index >= len(self.filtered_ids):
            return
        
        case_id = self.filtered_ids[self.current_index]
        new_annotation = self.anno_text.get(1.0, tk.END).strip()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE cases SET annotations = ? WHERE id = ?", (new_annotation, case_id))
        conn.commit()
        conn.close()
        
    def select_diseases(self):
        """选择疾病筛选类别（带滚动条优化版）"""
        if not self.all_diseases:
            messagebox.showwarning("警告", "没有可用的疾病类别")
            return
        
        select_window = tk.Toplevel(self.root)
        select_window.title("选择筛选类别")
        select_window.geometry("450x500")
        select_window.transient(self.root)
        select_window.grab_set()
        
        main_frame = ttk.Frame(select_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        vars_list = []
        
        for i, disease in enumerate(self.all_diseases):
            var = tk.BooleanVar(value=disease in self.selected_diseases)
            vars_list.append(var)
            cb = ttk.Checkbutton(scrollable_frame, text=disease, variable=var)
            cb.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        
        btn_frame = ttk.Frame(select_window)
        btn_frame.pack(pady=10, padx=10)
        
        def confirm_selection():
            self.selected_diseases = [self.all_diseases[i] for i, var in enumerate(vars_list) if var.get()]
            select_window.destroy()
            self.load_data()
        
        ttk.Button(btn_frame, text="确定", command=confirm_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=select_window.destroy).pack(side=tk.LEFT, padx=5)
        
        def select_all():
            for var in vars_list:
                var.set(True)
        
        def clear_all():
            for var in vars_list:
                var.set(False)
        
        ttk.Button(btn_frame, text="全选", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空", command=clear_all).pack(side=tk.LEFT, padx=5)
        
    def previous_case(self):
        """上一个病例"""
        self.save_current_annotation()
        if self.filtered_ids and self.current_index > 0:
            self.current_index -= 1
            self.display_current_case()
        
    def next_case(self):
        """下一个病例"""
        self.save_current_annotation()
        if self.filtered_ids and self.current_index < len(self.filtered_ids) - 1:
            self.current_index += 1
            self.display_current_case()

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicalDataAnnotator(root)
    root.mainloop()