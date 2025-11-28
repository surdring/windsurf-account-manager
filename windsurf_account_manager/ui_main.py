from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from .models import Account, McpServerConfig, RuleConfig
from . import storage, mcp_rules, api_client, config_snapshot, config_path_manager, auto_backup


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Windsurf Account Manager")
        self.root.geometry("900x600")

        self.accounts: List[Account] = storage.load_accounts()
        self.active_account_id = None
        
        # 初始化配置快照管理器
        self.snapshot_manager = config_snapshot.ConfigSnapshot()
        
        # 初始化配置路径管理器
        self.path_manager = config_path_manager.ConfigPathManager()
        
        # 初始化自动备份管理器
        self.auto_backup_manager = auto_backup.AutoBackupManager(
            config_path_manager=self.path_manager,
            snapshot_manager=self.snapshot_manager
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.accounts_frame = ttk.Frame(self.notebook)
        self.tools_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.accounts_frame, text="账号管理")
        self.notebook.add(self.tools_frame, text="工具")

        self._build_accounts_tab()
        self._build_tools_tab()
        
        # 初始化自动备份状态
        self.load_backup_config()
        self.update_backup_status()
        
        # 绑定标签页切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def _build_accounts_tab(self) -> None:
        toolbar = ttk.Frame(self.accounts_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)

        btn_import = ttk.Button(toolbar, text="从 windsuf.json 导入", command=self.on_import_windsurf_json)
        btn_export = ttk.Button(toolbar, text="导出账号", command=self.on_export_accounts)
        btn_delete = ttk.Button(toolbar, text="批量删除", command=self.on_delete_selected)
        btn_refresh = ttk.Button(toolbar, text="刷新列表", command=self.refresh_accounts_view)
        btn_select_all = ttk.Button(toolbar, text="全选", command=self.on_select_all)
        btn_clear_sel = ttk.Button(toolbar, text="全不选", command=self.on_clear_selection)
        btn_edit = ttk.Button(toolbar, text="编辑详情", command=self.on_edit_selected)
        btn_switch = ttk.Button(toolbar, text="切换到选中账号", command=self.on_switch_account)
        btn_login = ttk.Button(toolbar, text="登录选中账号", command=self.on_login_account)
        btn_snapshot = ttk.Button(toolbar, text="创建配置快照", command=self.on_create_snapshot)
        btn_restore = ttk.Button(toolbar, text="恢复配置快照", command=self.on_restore_snapshot)

        btn_import.pack(side=tk.LEFT, padx=4)
        btn_export.pack(side=tk.LEFT, padx=4)
        btn_delete.pack(side=tk.LEFT, padx=4)
        btn_refresh.pack(side=tk.LEFT, padx=4)
        btn_select_all.pack(side=tk.LEFT, padx=4)
        btn_clear_sel.pack(side=tk.LEFT, padx=4)
        btn_edit.pack(side=tk.LEFT, padx=4)
        btn_switch.pack(side=tk.LEFT, padx=4)
        btn_login.pack(side=tk.LEFT, padx=4)
        btn_snapshot.pack(side=tk.LEFT, padx=4)
        btn_restore.pack(side=tk.LEFT, padx=4)

        columns = ("email", "note", "plan_name", "plan_end", "snapshot")
        self.tree = ttk.Treeview(self.accounts_frame, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("email", text="邮箱")
        self.tree.heading("note", text="备注")
        self.tree.heading("plan_name", text="计划")
        self.tree.heading("plan_end", text="到期时间")
        self.tree.heading("snapshot", text="配置快照")

        self.tree.column("email", width=220)
        self.tree.column("note", width=150)
        self.tree.column("plan_name", width=120)
        self.tree.column("plan_end", width=140)
        self.tree.column("snapshot", width=100)

        vsb = ttk.Scrollbar(self.accounts_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.accounts_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.tag_configure("active_account", background="#d0f0ff")
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=4)
        hsb.pack(side=tk.BOTTOM, fill=tk.X, padx=8)

        self.refresh_accounts_view()

    def _build_tools_tab(self) -> None:
        # 创建工具标签页的子标签页
        tools_notebook = ttk.Notebook(self.tools_frame)
        tools_notebook.pack(fill=tk.BOTH, expand=True)
        
        # MCP/Rules 子标签页
        self.mcp_rules_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(self.mcp_rules_frame, text="MCP / Rules")
        self._build_mcp_rules_tab()
        
        # 配置路径管理 子标签页
        self.config_paths_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(self.config_paths_frame, text="配置路径管理")
        self._build_config_paths_tab()
        
        # 自动备份 子标签页
        self.auto_backup_frame = ttk.Frame(tools_notebook)
        tools_notebook.add(self.auto_backup_frame, text="自动备份")
        self._build_auto_backup_tab()
    
    def _build_mcp_rules_tab(self) -> None:
        self.mcp_servers: List[McpServerConfig] = []
        self.rules: List[RuleConfig] = []
        self.mcp_config_path: Optional[Path] = None
        self.rules_config_path: Optional[Path] = None

        # MCP 区域
        frame_mcp = ttk.Frame(self.mcp_rules_frame)
        frame_mcp.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        mcp_toolbar = ttk.Frame(frame_mcp)
        mcp_toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_mcp_open = ttk.Button(mcp_toolbar, text="打开 MCP 文件", command=self.on_open_mcp_file)
        btn_mcp_save = ttk.Button(mcp_toolbar, text="保存 MCP 文件", command=self.on_save_mcp_file)
        btn_mcp_backup = ttk.Button(mcp_toolbar, text="备份 MCP...", command=self.on_backup_mcp)
        btn_mcp_add = ttk.Button(mcp_toolbar, text="新建", command=self.on_add_mcp)
        btn_mcp_edit = ttk.Button(mcp_toolbar, text="编辑", command=self.on_edit_mcp)
        btn_mcp_delete = ttk.Button(mcp_toolbar, text="删除", command=self.on_delete_mcp)

        for btn in (btn_mcp_open, btn_mcp_save, btn_mcp_backup, btn_mcp_add, btn_mcp_edit, btn_mcp_delete):
            btn.pack(side=tk.LEFT, padx=4, pady=4)

        mcp_columns = ("id", "name", "command", "enabled")
        self.tree_mcp = ttk.Treeview(frame_mcp, columns=mcp_columns, show="headings", selectmode="extended")

        self.tree_mcp.heading("id", text="ID")
        self.tree_mcp.heading("name", text="名称")
        self.tree_mcp.heading("command", text="命令")
        self.tree_mcp.heading("enabled", text="启用")

        self.tree_mcp.column("id", width=170)
        self.tree_mcp.column("name", width=140)
        self.tree_mcp.column("command", width=240)
        self.tree_mcp.column("enabled", width=60, anchor=tk.CENTER)

        mcp_vsb = ttk.Scrollbar(frame_mcp, orient="vertical", command=self.tree_mcp.yview)
        self.tree_mcp.configure(yscrollcommand=mcp_vsb.set)

        self.tree_mcp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(4, 0))
        mcp_vsb.pack(side=tk.LEFT, fill=tk.Y, pady=(4, 0))

        self.tree_mcp.bind("<Double-1>", self.on_tree_mcp_double_click)

        # Rules 区域
        frame_rules = ttk.Frame(self.mcp_rules_frame)
        frame_rules.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        rules_toolbar = ttk.Frame(frame_rules)
        rules_toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_rules_open = ttk.Button(rules_toolbar, text="打开 Rules 文件", command=self.on_open_rules_file)
        btn_rules_save = ttk.Button(rules_toolbar, text="保存 Rules 文件", command=self.on_save_rules_file)
        btn_rules_backup = ttk.Button(rules_toolbar, text="备份 Rules...", command=self.on_backup_rules)
        btn_rules_add = ttk.Button(rules_toolbar, text="新建", command=self.on_add_rule)
        btn_rules_edit = ttk.Button(rules_toolbar, text="编辑", command=self.on_edit_rule)
        btn_rules_delete = ttk.Button(rules_toolbar, text="删除", command=self.on_delete_rules)

        for btn in (btn_rules_open, btn_rules_save, btn_rules_backup, btn_rules_add, btn_rules_edit, btn_rules_delete):
            btn.pack(side=tk.LEFT, padx=4, pady=4)

        rules_columns = ("id", "prompt")
        self.tree_rules = ttk.Treeview(frame_rules, columns=rules_columns, show="headings", selectmode="extended")

        self.tree_rules.heading("id", text="ID")
        self.tree_rules.heading("prompt", text="提示词")

        self.tree_rules.column("id", width=170)
        self.tree_rules.column("prompt", width=260)

        rules_vsb = ttk.Scrollbar(frame_rules, orient="vertical", command=self.tree_rules.yview)
        self.tree_rules.configure(yscrollcommand=rules_vsb.set)

        self.tree_rules.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(4, 0))
        rules_vsb.pack(side=tk.LEFT, fill=tk.Y, pady=(4, 0))

        self.tree_rules.bind("<Double-1>", self.on_tree_rules_double_click)
    
    def on_tab_changed(self, event) -> None:
        """标签页切换事件处理"""
        selected_tab = event.widget.tab('current')['text']
        if selected_tab == "自动备份":
            self.refresh_auto_backup_view()
            self.update_backup_status()

        self.refresh_mcp_view()
        self.refresh_rules_view()
    
    def _build_config_paths_tab(self) -> None:
        # 工具栏
        toolbar = ttk.Frame(self.config_paths_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        
        btn_auto_detect = ttk.Button(toolbar, text="自动检测", command=self.on_auto_detect_paths)
        btn_add_path = ttk.Button(toolbar, text="添加路径", command=self.on_add_config_path)
        btn_remove_path = ttk.Button(toolbar, text="删除路径", command=self.on_remove_config_path)
        btn_set_active = ttk.Button(toolbar, text="设为活动", command=self.on_set_active_path)
        btn_refresh = ttk.Button(toolbar, text="刷新", command=self.refresh_config_paths_view)
        
        btn_auto_detect.pack(side=tk.LEFT, padx=4)
        btn_add_path.pack(side=tk.LEFT, padx=4)
        btn_remove_path.pack(side=tk.LEFT, padx=4)
        btn_set_active.pack(side=tk.LEFT, padx=4)
        btn_refresh.pack(side=tk.LEFT, padx=4)
        
        # 配置路径列表
        columns = ("name", "path", "has_config", "active")
        self.tree_paths = ttk.Treeview(self.config_paths_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree_paths.heading("name", text="名称")
        self.tree_paths.heading("path", text="路径")
        self.tree_paths.heading("has_config", text="包含配置")
        self.tree_paths.heading("active", text="活动")
        
        self.tree_paths.column("name", width=150)
        self.tree_paths.column("path", width=300)
        self.tree_paths.column("has_config", width=100, anchor=tk.CENTER)
        self.tree_paths.column("active", width=60, anchor=tk.CENTER)
        
        vsb = ttk.Scrollbar(self.config_paths_frame, orient="vertical", command=self.tree_paths.yview)
        hsb = ttk.Scrollbar(self.config_paths_frame, orient="horizontal", command=self.tree_paths.xview)
        self.tree_paths.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree_paths.tag_configure("active_path", background="#d0f0ff")
        
        self.tree_paths.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=4)
        hsb.pack(side=tk.BOTTOM, fill=tk.X, padx=8)
        
        self.refresh_config_paths_view()
    
    def refresh_config_paths_view(self) -> None:
        """刷新配置路径视图"""
        for item in self.tree_paths.get_children():
            self.tree_paths.delete(item)
        
        paths = self.path_manager.get_paths()
        active_path = self.path_manager.get_active_path()
        active_path_str = str(active_path) if active_path else ""
        
        for path_info in paths:
            path = path_info.get("path", "")
            is_active = (path == active_path_str)
            tags = ("active_path",) if is_active else ()
            
            self.tree_paths.insert(
                "",
                tk.END,
                iid=str(path_info.get("id")),
                values=(
                    path_info.get("name", ""),
                    path_info.get("path", ""),
                    "是" if path_info.get("has_config") else "否",
                    "是" if is_active else "否"
                ),
                tags=tags
            )
    
    def on_auto_detect_paths(self) -> None:
        """自动检测配置路径"""
        detected_paths = self.path_manager.detect_windsurf_paths()
        
        if not detected_paths:
            messagebox.showinfo(
                "自动检测",
                "未检测到Windsurf配置路径。\n\n"
                "请手动添加配置路径。"
            )
            return
        
        # 筛选出尚未添加的路径
        new_paths = []
        for path in detected_paths:
            if not self.path_manager.path_exists(path):
                # 验证路径
                validation_result = self.path_manager.validate_path(path)
                if validation_result["valid"]:
                    new_paths.append((path, validation_result))
        
        if not new_paths:
            messagebox.showinfo(
                "自动检测",
                "未发现新的Windsurf配置路径。\n\n"
                "所有检测到的路径都已存在于配置路径列表中。"
            )
            return
        
        # 显示检测结果并询问是否添加
        msg = f"检测到 {len(new_paths)} 个新的Windsurf配置路径:\n\n"
        for i, (path, _) in enumerate(new_paths, 1):
            msg += f"{i}. {path}\n"
        
        msg += "\n是否添加这些路径？"
        
        if not messagebox.askyesno("自动检测", msg):
            return
        
        # 添加路径
        added_count = 0
        for path, validation_result in new_paths:
            path_id = self.path_manager.add_path(path)
            if path_id:
                added_count += 1
        
        if added_count > 0:
            self.refresh_config_paths_view()
            messagebox.showinfo(
                "添加完成",
                f"已成功添加 {added_count} 个配置路径。"
            )
            
            # 如果有警告信息，显示给用户
            warnings = []
            for _, validation_result in new_paths:
                if validation_result["warnings"]:
                    warnings.extend(validation_result["warnings"])
            
            if warnings:
                warning_msg = "部分路径存在以下警告:\n\n"
                warning_msg += "\n".join(warnings)
                messagebox.showwarning("路径警告", warning_msg)
        else:
            messagebox.showerror("添加失败", "添加配置路径时发生错误。")
    
    def on_add_config_path(self) -> None:
        """添加配置路径"""
        path_str = filedialog.askdirectory(
            title="选择Windsurf配置目录",
            initialdir=str(self.path_manager.get_default_path() or Path.home())
        )
        
        if not path_str:
            return
        
        path = Path(path_str)
        validation = self.path_manager.validate_path(path)
        
        if not validation["exists"]:
            messagebox.showerror("添加路径失败", "选择的路径不存在。")
            return
        
        if not validation["valid"]:
            error_msg = "所选路径不是有效的Windsurf配置目录:\n\n"
            error_msg += "\n".join(validation["errors"])
            
            result = messagebox.askyesno(
                "确认添加",
                f"{error_msg}\n\n"
                f"路径: {path}\n\n"
                f"是否仍要添加？"
            )
            if not result:
                return
        
        # 弹出对话框输入名称
        dialog = tk.Toplevel(self.root)
        dialog.title("添加配置路径")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="路径名称:").pack(pady=10)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=5)
        name_entry.insert(0, path.name)
        name_entry.select_range(0, tk.END)
        name_entry.focus_set()
        
        def on_confirm():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("添加路径失败", "请输入路径名称。")
                return
            
            if self.path_manager.add_path(path, name):
                self.refresh_config_paths_view()
                messagebox.showinfo("添加成功", f"已添加配置路径: {name}")
                dialog.destroy()
            else:
                messagebox.showerror("添加路径失败", "该路径可能已存在。")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def on_remove_config_path(self) -> None:
        """删除配置路径"""
        selected = list(self.tree_paths.selection())
        if not selected:
            messagebox.showinfo("删除路径", "请先选择要删除的路径。")
            return
        
        path_id = int(selected[0])
        path_info = next((p for p in self.path_manager.get_paths() if p.get("id") == path_id), None)
        
        if not path_info:
            return
        
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除以下配置路径吗？\n\n"
            f"名称: {path_info.get('name', '')}\n"
            f"路径: {path_info.get('path', '')}\n\n"
            f"注意: 这不会删除实际的配置文件，仅从管理器中移除。"
        )
        
        if result:
            if self.path_manager.remove_path(path_id):
                self.refresh_config_paths_view()
                messagebox.showinfo("删除成功", "配置路径已删除。")
            else:
                messagebox.showerror("删除失败", "删除配置路径时发生错误。")
    
    def on_set_active_path(self) -> None:
        """设置活动配置路径"""
        selected = list(self.tree_paths.selection())
        if not selected:
            messagebox.showinfo("设置活动路径", "请先选择要设为活动的路径。")
            return
        
        path_id = int(selected[0])
        path_info = next((p for p in self.path_manager.get_paths() if p.get("id") == path_id), None)
        
        if not path_info:
            return
        
        # 获取当前活动路径用于比较
        current_active = self.path_manager.get_active_path()
        current_active_str = str(current_active) if current_active else ""
        selected_path_str = path_info.get("path", "")
        
        # 如果已经是活动路径，提示用户
        if current_active_str == selected_path_str:
            messagebox.showinfo("设置活动路径", "该路径已经是活动配置路径。")
            return
        
        # 转换为Path对象
        path = Path(selected_path_str)
        
        if self.path_manager.set_active_path(path):
            self.refresh_config_paths_view()
            messagebox.showinfo(
                "设置成功",
                f"已设置活动配置路径:\n\n"
                f"名称: {path_info.get('name', '')}\n"
                f"路径: {path_info.get('path', '')}"
            )
        else:
            messagebox.showerror("设置失败", "设置活动配置路径时发生错误。")

    def _build_auto_backup_tab(self) -> None:
        # 工具栏
        toolbar = ttk.Frame(self.auto_backup_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        
        btn_enable_backup = ttk.Button(toolbar, text="启用自动备份", command=self.on_enable_auto_backup)
        btn_disable_backup = ttk.Button(toolbar, text="禁用自动备份", command=self.on_disable_auto_backup)
        btn_backup_now = ttk.Button(toolbar, text="立即备份", command=self.on_backup_now)
        btn_restore_backup = ttk.Button(toolbar, text="恢复备份", command=self.on_restore_backup)
        btn_delete_backup = ttk.Button(toolbar, text="删除备份", command=self.on_delete_backup)
        btn_refresh = ttk.Button(toolbar, text="刷新", command=self.refresh_auto_backup_view)
        
        btn_enable_backup.pack(side=tk.LEFT, padx=4)
        btn_disable_backup.pack(side=tk.LEFT, padx=4)
        btn_backup_now.pack(side=tk.LEFT, padx=4)
        btn_restore_backup.pack(side=tk.LEFT, padx=4)
        btn_delete_backup.pack(side=tk.LEFT, padx=4)
        btn_refresh.pack(side=tk.LEFT, padx=4)
        
        # 配置区域
        config_frame = ttk.LabelFrame(self.auto_backup_frame, text="自动备份配置")
        config_frame.pack(fill=tk.X, padx=8, pady=4)
        
        # 备份间隔设置
        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(interval_frame, text="备份间隔:").pack(side=tk.LEFT, padx=4)
        self.backup_interval_var = tk.StringVar(value="24")
        interval_spinbox = ttk.Spinbox(interval_frame, from_=1, to=168, textvariable=self.backup_interval_var, width=10)
        interval_spinbox.pack(side=tk.LEFT, padx=4)
        ttk.Label(interval_frame, text="小时").pack(side=tk.LEFT, padx=4)
        
        # 最大备份数设置
        max_backups_frame = ttk.Frame(config_frame)
        max_backups_frame.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(max_backups_frame, text="最大备份数:").pack(side=tk.LEFT, padx=4)
        self.max_backups_var = tk.StringVar(value="5")
        max_backups_spinbox = ttk.Spinbox(max_backups_frame, from_=1, to=50, textvariable=self.max_backups_var, width=10)
        max_backups_spinbox.pack(side=tk.LEFT, padx=4)
        ttk.Label(max_backups_frame, text="个").pack(side=tk.LEFT, padx=4)
        
        # 保存配置按钮
        save_config_btn = ttk.Button(config_frame, text="保存配置", command=self.on_save_backup_config)
        save_config_btn.pack(pady=4)
        
        # 状态显示
        status_frame = ttk.LabelFrame(self.auto_backup_frame, text="状态")
        status_frame.pack(fill=tk.X, padx=8, pady=4)
        
        self.backup_status_text = tk.Text(status_frame, height=3, width=80)
        self.backup_status_text.pack(padx=8, pady=4)
        
        # 备份列表
        list_frame = ttk.LabelFrame(self.auto_backup_frame, text="备份列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        
        columns = ("account", "created_at", "path")
        self.tree_backups = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree_backups.heading("account", text="账号")
        self.tree_backups.heading("created_at", text="创建时间")
        self.tree_backups.heading("path", text="备份路径")
        
        self.tree_backups.column("account", width=200)
        self.tree_backups.column("created_at", width=180)
        self.tree_backups.column("path", width=300)
        
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_backups.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree_backups.xview)
        self.tree_backups.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree_backups.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=4)
        hsb.pack(side=tk.BOTTOM, fill=tk.X, padx=8)
        
        # 加载配置并刷新视图
        self.load_backup_config()
        self.refresh_auto_backup_view()
        self.update_backup_status()

    def refresh_accounts_view(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for acc in self.accounts:
            tags = ("active_account",) if acc.id == self.active_account_id else ()
            # 显示快照状态
            snapshot_status = "无"
            if acc.has_snapshot and acc.snapshot_created_at:
                snapshot_status = acc.snapshot_created_at[:10]  # 只显示日期部分
            
            self.tree.insert(
                "",
                tk.END,
                iid=acc.id,
                values=(acc.email, acc.note, acc.plan_name or "", acc.plan_end or "", snapshot_status),
                tags=tags,
            )

    def on_import_windsurf_json(self) -> None:
        path_str = filedialog.askopenfilename(
            title="选择 windsuf.json",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self.accounts = storage.import_from_windsurf_json(path, self.accounts)
            storage.save_accounts(self.accounts)
            self.refresh_accounts_view()
        except Exception as exc:
            messagebox.showerror("导入失败", f"导入 windsuf.json 失败: {exc}")

    def on_export_accounts(self) -> None:
        path_str = filedialog.asksaveasfilename(
            title="导出账号",
            defaultextension=".json",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            storage.export_accounts(path, self.accounts)
        except Exception as exc:
            messagebox.showerror("导出失败", f"导出账号失败: {exc}")

    def on_delete_selected(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            return
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected)} 个账号吗？"):
            return
        remaining = [a for a in self.accounts if a.id not in selected]
        self.accounts = remaining
        if self.active_account_id in selected:
            self.active_account_id = None
        storage.save_accounts(self.accounts)
        self.refresh_accounts_view()

    def on_select_all(self) -> None:
        items = self.tree.get_children()
        if not items:
            return
        self.tree.selection_set(items)

    def on_clear_selection(self) -> None:
        self.tree.selection_remove(self.tree.selection())

    def on_edit_selected(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            messagebox.showinfo("编辑详情", "请先选择一个账号。")
            return
        if len(selected) > 1:
            messagebox.showinfo("编辑详情", "一次仅支持编辑一个账号，请只选择一个账号。")
            return
        self._edit_account(selected[0])

    def on_tree_double_click(self, _event: tk.Event) -> None:  # type: ignore[override]
        item_id = self.tree.focus()
        if not item_id:
            return
        self._edit_account(item_id)

    def _edit_account(self, acc_id: str) -> None:
        acc = next((a for a in self.accounts if a.id == acc_id), None)
        if acc is None:
            return

        win = tk.Toplevel(self.root)
        win.title("编辑账号详情")
        win.transient(self.root)
        win.grab_set()

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="邮箱:").grid(row=0, column=0, sticky=tk.W, pady=4)
        email_var = tk.StringVar(value=acc.email)
        ent_email = ttk.Entry(frm, textvariable=email_var, state="readonly", width=40)
        ent_email.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="备注:").grid(row=1, column=0, sticky=tk.W, pady=4)
        note_var = tk.StringVar(value=acc.note)
        ent_note = ttk.Entry(frm, textvariable=note_var, width=40)
        ent_note.grid(row=1, column=1, sticky=tk.W, pady=4)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(12, 0))

        def on_ok() -> None:
            acc.note = note_var.get()
            storage.save_accounts(self.accounts)
            self.refresh_accounts_view()
            win.destroy()

        def on_cancel() -> None:
            win.destroy()

        btn_ok = ttk.Button(btn_frame, text="保存", command=on_ok)
        btn_cancel = ttk.Button(btn_frame, text="取消", command=on_cancel)
        btn_ok.pack(side=tk.LEFT, padx=4)
        btn_cancel.pack(side=tk.LEFT, padx=4)

        win.bind("<Return>", lambda _e: on_ok())
        win.bind("<Escape>", lambda _e: on_cancel())

    def on_switch_account(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            messagebox.showinfo("切换账号", "请先选择一个要切换的账号。")
            return
        if len(selected) > 1:
            messagebox.showinfo("切换账号", "一次仅支持切换到一个账号，请只选择一个账号。")
            return

        acc_id = selected[0]
        acc = next((a for a in self.accounts if a.id == acc_id), None)
        if acc is None:
            return

        self.active_account_id = acc_id
        self.refresh_accounts_view()

        messagebox.showinfo(
            "切换账号",
            f"已在管理器中切换到账号: {acc.email}\n\n后续将基于此账号执行切号相关操作（例如配置切换或外部登录脚本）。",
        )

    def on_login_account(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            messagebox.showinfo("登录账号", "请先选择一个要登录的账号。")
            return
        if len(selected) > 1:
            messagebox.showinfo("登录账号", "一次仅支持登录一个账号，请只选择一个账号。")
            return

        acc_id = selected[0]
        acc = next((a for a in self.accounts if a.id == acc_id), None)
        if acc is None:
            return

        if not acc.password:
            messagebox.showerror("登录失败", "该账号未保存密码，无法自动登录。")
            return

        # 显示登录进度对话框
        progress_win = tk.Toplevel(self.root)
        progress_win.title("登录中...")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_frame = ttk.Frame(progress_win)
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        ttk.Label(progress_frame, text="正在登录，请稍候...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
        progress_bar.pack(fill=tk.X, pady=10)
        progress_bar.start()

        def login_thread():
            try:
                client = api_client.ApiClient()
                success = client.login_and_update_account(acc)
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self._login_complete(acc, success, progress_win))
            except Exception as e:
                self.root.after(0, lambda: self._login_error(str(e), progress_win))

        # 在新线程中执行登录
        import threading
        thread = threading.Thread(target=login_thread)
        thread.daemon = True
        thread.start()

    def _login_complete(self, account: Account, success: bool, progress_win: tk.Toplevel) -> None:
        progress_win.destroy()
        
        if success:
            storage.save_accounts(self.accounts)
            self.refresh_accounts_view()
            messagebox.showinfo(
                "登录成功",
                f"账号 {account.email} 登录成功！\n\n"
                f"计划: {account.plan_name or '未知'}\n"
                f"到期时间: {account.plan_end or '未知'}\n"
                f"已用提示词: {account.used_prompt_credits or 0}\n"
                f"已用流程: {account.used_flow_credits or 0}"
            )
        else:
            messagebox.showerror("登录失败", "登录失败，请检查账号密码是否正确。")

    def _login_error(self, error_msg: str, progress_win: tk.Toplevel) -> None:
        progress_win.destroy()
        messagebox.showerror("登录错误", f"登录过程中发生错误：{error_msg}")

    def on_create_snapshot(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            messagebox.showinfo("创建配置快照", "请先选择一个账号。")
            return
        if len(selected) > 1:
            messagebox.showinfo("创建配置快照", "一次仅支持为一个账号创建配置快照。")
            return

        acc_id = selected[0]
        acc = next((a for a in self.accounts if a.id == acc_id), None)
        if acc is None:
            return

        if acc.has_snapshot:
            confirm = messagebox.askyesno(
                "覆盖快照",
                f"账号 {acc.email} 已有配置快照，创建于 {acc.snapshot_created_at}。\n\n"
                "是否覆盖现有快照？"
            )
            if not confirm:
                return

        # 使用配置路径管理器中的活动路径
        active_path = self.path_manager.get_active_path()
        if not active_path:
            messagebox.showerror(
                "创建配置快照失败",
                "没有设置活动配置路径。\n\n"
                "请在'配置路径管理'标签页中设置活动路径。"
            )
            return

        # 确保active_path是Path对象
        if not isinstance(active_path, Path):
            active_path = Path(active_path)

        # 询问快照名称
        from tkinter import simpledialog
        snapshot_name = simpledialog.askstring(
            "创建配置快照",
            f"为账号 {acc.email} 创建配置快照\n\n请输入快照名称:",
            initialvalue=f"{acc.email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        if not snapshot_name:
            return

        # 创建快照
        success = self.snapshot_manager.create_snapshot(acc.id, active_path, snapshot_name)
        if success:
            # 更新账号信息
            acc.has_snapshot = True
            acc.snapshot_created_at = datetime.now().isoformat()
            storage.save_accounts(self.accounts)
            self.refresh_accounts_view()
            
            messagebox.showinfo(
                "创建配置快照成功",
                f"已为账号 {acc.email} 创建配置快照: {snapshot_name}\n\n"
                f"快照保存在: {self.snapshot_manager.get_account_snapshot_dir(acc.id)}"
            )
        else:
            messagebox.showerror("创建配置快照失败", "创建配置快照时发生错误，请检查权限和路径。")

    def on_restore_snapshot(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            messagebox.showinfo("恢复配置快照", "请先选择一个账号。")
            return
        if len(selected) > 1:
            messagebox.showinfo("恢复配置快照", "一次仅支持为一个账号恢复配置快照。")
            return

        acc_id = selected[0]
        acc = next((a for a in self.accounts if a.id == acc_id), None)
        if acc is None:
            return

        if not acc.has_snapshot:
            messagebox.showerror("恢复配置快照失败", f"账号 {acc.email} 没有配置快照。")
            return

        # 使用配置路径管理器中的活动路径
        active_path = self.path_manager.get_active_path()
        if not active_path:
            messagebox.showerror(
                "恢复配置快照失败",
                "没有设置活动配置路径。\n\n"
                "请在'配置路径管理'标签页中设置活动路径。"
            )
            return

        # 确保active_path是Path对象
        if not isinstance(active_path, Path):
            active_path = Path(active_path)

        # 获取快照信息
        snapshot = self.snapshot_manager.get_snapshot(acc_id)
        if not snapshot:
            messagebox.showerror("恢复配置快照失败", "快照不存在。")
            return

        # 确认恢复操作
        confirm = messagebox.askyesno(
            "确认恢复",
            f"恢复配置快照将覆盖当前的Windsurf配置。\n\n"
            f"账号: {acc.email}\n"
            f"快照名称: {snapshot.get('name', '未知')}\n"
            f"快照创建时间: {acc.snapshot_created_at}\n"
            f"目标路径: {active_path}\n\n"
            f"是否继续？"
        )
        
        if not confirm:
            return

        # 恢复快照
        success = self.snapshot_manager.restore_snapshot(acc.id, active_path)
        if success:
            messagebox.showinfo(
                "恢复配置快照成功",
                f"已为账号 {acc.email} 恢复配置快照。\n\n"
                f"快照名称: {snapshot.get('name', '未知')}\n"
                f"建议重启Windsurf以使配置生效。"
            )
        else:
            messagebox.showerror("恢复配置快照失败", "恢复配置快照时发生错误，请检查权限和路径。")

    def on_delete_snapshot(self) -> None:
        """删除快照"""
        selected = list(self.tree.selection())
        if not selected:
            messagebox.showinfo("删除快照", "请先选择要删除快照的账号。")
            return
        if len(selected) > 1:
            messagebox.showinfo("删除快照", "一次仅支持为一个账号删除快照。")
            return

        acc_id = selected[0]
        acc = next((a for a in self.accounts if a.id == acc_id), None)
        if acc is None:
            return

        if not acc.has_snapshot:
            messagebox.showerror("删除快照失败", f"账号 {acc.email} 没有配置快照。")
            return

        # 使用配置路径管理器中的活动路径
        active_path = self.path_manager.get_active_path()
        if not active_path:
            messagebox.showerror(
                "删除快照失败",
                "没有设置活动配置路径。\n\n"
                "请在'配置路径管理'标签页中设置活动路径。"
            )
            return

        # 确保active_path是Path对象
        if not isinstance(active_path, Path):
            active_path = Path(active_path)

        # 获取快照信息
        snapshot = self.snapshot_manager.get_snapshot(acc_id)
        snapshot_name = snapshot.get('name', '未知') if snapshot else '未知'

        # 确认删除操作
        confirm = messagebox.askyesno(
            "确认删除快照",
            f"确定要删除以下账号的配置快照吗？\n\n"
            f"账号: {acc.email}\n"
            f"快照名称: {snapshot_name}\n"
            f"快照创建时间: {acc.snapshot_created_at}\n"
            f"当前活动路径: {active_path}\n\n"
            f"注意: 此操作不可撤销。"
        )
        
        if not confirm:
            return

        # 删除快照
        success = self.snapshot_manager.delete_snapshot(acc.id)
        if success:
            # 更新账号信息
            acc.has_snapshot = False
            acc.snapshot_created_at = None
            storage.save_accounts(self.accounts)
            self.refresh_accounts_view()
            messagebox.showinfo("删除快照成功", f"已删除账号 {acc.email} 的配置快照。")
        else:
            messagebox.showerror("删除快照失败", "删除配置快照时发生错误，请检查权限和路径。")

    # MCP / Rules 相关逻辑

    def refresh_mcp_view(self) -> None:
        if not hasattr(self, "tree_mcp"):
            return
        for item in self.tree_mcp.get_children():
            self.tree_mcp.delete(item)
        for server in self.mcp_servers:
            enabled_text = "是" if server.enabled else "否"
            self.tree_mcp.insert(
                "",
                tk.END,
                iid=server.id,
                values=(server.id, server.name, server.command, enabled_text),
            )

    def refresh_rules_view(self) -> None:
        if not hasattr(self, "tree_rules"):
            return
        for item in self.tree_rules.get_children():
            self.tree_rules.delete(item)
        for rule in self.rules:
            prompt_display = rule.prompt.replace("\n", " ")
            if len(prompt_display) > 60:
                prompt_display = prompt_display[:57] + "..."
            self.tree_rules.insert(
                "",
                tk.END,
                iid=rule.id,
                values=(rule.id, prompt_display),
            )

    def on_open_mcp_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="选择 MCP 配置 JSON",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self.mcp_servers = mcp_rules.load_mcp_config(path)
            self.mcp_config_path = path
            self.refresh_mcp_view()
        except Exception as exc:
            messagebox.showerror("打开 MCP 文件失败", f"读取 MCP 配置失败: {exc}")

    def on_save_mcp_file(self) -> None:
        if self.mcp_config_path is None:
            path_str = filedialog.asksaveasfilename(
                title="保存 MCP 配置 JSON",
                defaultextension=".json",
                filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
            )
            if not path_str:
                return
            self.mcp_config_path = Path(path_str)
        try:
            mcp_rules.save_mcp_config(self.mcp_config_path, self.mcp_servers)
        except Exception as exc:
            messagebox.showerror("保存 MCP 文件失败", f"写入 MCP 配置失败: {exc}")

    def on_backup_mcp(self) -> None:
        if not self.mcp_servers:
            if not messagebox.askyesno("备份 MCP", "当前 MCP 列表为空，仍要备份为空配置吗？"):
                return
        path_str = filedialog.asksaveasfilename(
            title="选择 MCP 备份文件保存路径",
            defaultextension=".json",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            mcp_rules.save_mcp_config(path, self.mcp_servers)
        except Exception as exc:
            messagebox.showerror("备份 MCP 失败", f"写入 MCP 备份失败: {exc}")

    def on_add_mcp(self) -> None:
        self._edit_mcp_server(None)

    def on_edit_mcp(self) -> None:
        selected = list(self.tree_mcp.selection())
        if not selected:
            messagebox.showinfo("编辑 MCP", "请先选择一个 MCP 配置。")
            return
        if len(selected) > 1:
            messagebox.showinfo("编辑 MCP", "一次仅支持编辑一个 MCP 配置。")
            return
        server = next((s for s in self.mcp_servers if s.id == selected[0]), None)
        if server is None:
            return
        self._edit_mcp_server(server)

    def on_tree_mcp_double_click(self, _event: tk.Event) -> None:  # type: ignore[override]
        item_id = self.tree_mcp.focus()
        if not item_id:
            return
        server = next((s for s in self.mcp_servers if s.id == item_id), None)
        if server is None:
            return
        self._edit_mcp_server(server)

    def _edit_mcp_server(self, server: Optional[McpServerConfig]) -> None:
        editing = server is not None

        win = tk.Toplevel(self.root)
        win.title("编辑 MCP" if editing else "新建 MCP")
        win.transient(self.root)
        win.grab_set()

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="ID:").grid(row=0, column=0, sticky=tk.W, pady=4)
        id_var = tk.StringVar(value=server.id if editing else str(uuid4()))
        ent_id = ttk.Entry(frm, textvariable=id_var, width=40)
        ent_id.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="名称:").grid(row=1, column=0, sticky=tk.W, pady=4)
        name_var = tk.StringVar(value=server.name if editing else "")
        ent_name = ttk.Entry(frm, textvariable=name_var, width=40)
        ent_name.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="命令:").grid(row=2, column=0, sticky=tk.W, pady=4)
        command_var = tk.StringVar(value=server.command if editing else "")
        ent_command = ttk.Entry(frm, textvariable=command_var, width=40)
        ent_command.grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="参数(空格分隔):").grid(row=3, column=0, sticky=tk.W, pady=4)
        args_value = "" if not editing else " ".join(server.args)
        args_var = tk.StringVar(value=args_value)
        ent_args = ttk.Entry(frm, textvariable=args_var, width=40)
        ent_args.grid(row=3, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="环境变量(KEY=VALUE 每行一条):").grid(row=4, column=0, sticky=tk.NW, pady=4)
        txt_env = tk.Text(frm, width=40, height=5)
        if editing and server.env:
            lines = [f"{k}={v}" for k, v in server.env.items()]
            txt_env.insert("1.0", "\n".join(lines))
        txt_env.grid(row=4, column=1, sticky=tk.W, pady=4)

        enabled_var = tk.BooleanVar(value=server.enabled if editing else True)
        chk_enabled = ttk.Checkbutton(frm, text="启用", variable=enabled_var)
        chk_enabled.grid(row=5, column=1, sticky=tk.W, pady=(4, 0))

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(12, 0))

        def on_ok() -> None:
            id_val = id_var.get().strip()
            if not id_val:
                messagebox.showerror("保存 MCP", "ID 不能为空。")
                return
            name_val = name_var.get().strip()
            command_val = command_var.get().strip()
            args_str = args_var.get().strip()
            args_list = [a for a in args_str.split(" ") if a]

            env_text = txt_env.get("1.0", tk.END).strip()
            env_dict = {}
            if env_text:
                for line in env_text.splitlines():
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    env_dict[k.strip()] = v.strip()

            if editing and server is not None:
                server.id = id_val
                server.name = name_val
                server.command = command_val
                server.args = args_list
                server.env = env_dict
                server.enabled = enabled_var.get()
            else:
                new_server = McpServerConfig(
                    id=id_val,
                    name=name_val,
                    command=command_val,
                    args=args_list,
                    env=env_dict,
                    enabled=enabled_var.get(),
                )
                self.mcp_servers.append(new_server)

            self.refresh_mcp_view()
            win.destroy()

        def on_cancel() -> None:
            win.destroy()

        btn_ok = ttk.Button(btn_frame, text="保存", command=on_ok)
        btn_cancel = ttk.Button(btn_frame, text="取消", command=on_cancel)
        btn_ok.pack(side=tk.LEFT, padx=4)
        btn_cancel.pack(side=tk.LEFT, padx=4)

        win.bind("<Return>", lambda _e: on_ok())
        win.bind("<Escape>", lambda _e: on_cancel())

    def on_delete_mcp(self) -> None:
        selected = list(self.tree_mcp.selection())
        if not selected:
            return
        if not messagebox.askyesno("删除 MCP", f"确定要删除选中的 {len(selected)} 条 MCP 配置吗？"):
            return
        self.mcp_servers = [s for s in self.mcp_servers if s.id not in selected]
        self.refresh_mcp_view()

    def on_open_rules_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="选择 Rules 配置 JSON",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self.rules = mcp_rules.load_rules(path)
            self.rules_config_path = path
            self.refresh_rules_view()
        except Exception as exc:
            messagebox.showerror("打开 Rules 文件失败", f"读取 Rules 配置失败: {exc}")

    def on_save_rules_file(self) -> None:
        if self.rules_config_path is None:
            path_str = filedialog.asksaveasfilename(
                title="保存 Rules 配置 JSON",
                defaultextension=".json",
                filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
            )
            if not path_str:
                return
            self.rules_config_path = Path(path_str)
        try:
            mcp_rules.save_rules(self.rules_config_path, self.rules)
        except Exception as exc:
            messagebox.showerror("保存 Rules 文件失败", f"写入 Rules 配置失败: {exc}")

    def on_backup_rules(self) -> None:
        if not self.rules:
            if not messagebox.askyesno("备份 Rules", "当前 Rules 列表为空，仍要备份为空配置吗？"):
                return
        path_str = filedialog.asksaveasfilename(
            title="选择 Rules 备份文件保存路径",
            defaultextension=".json",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            mcp_rules.save_rules(path, self.rules)
        except Exception as exc:
            messagebox.showerror("备份 Rules 失败", f"写入 Rules 备份失败: {exc}")

    def on_add_rule(self) -> None:
        self._edit_rule(None)

    def on_edit_rule(self) -> None:
        selected = list(self.tree_rules.selection())
        if not selected:
            messagebox.showinfo("编辑 Rule", "请先选择一个 Rule。")
            return
        if len(selected) > 1:
            messagebox.showinfo("编辑 Rule", "一次仅支持编辑一个 Rule。")
            return
        rule = next((r for r in self.rules if r.id == selected[0]), None)
        if rule is None:
            return
        self._edit_rule(rule)

    def on_tree_rules_double_click(self, _event: tk.Event) -> None:  # type: ignore[override]
        item_id = self.tree_rules.focus()
        if not item_id:
            return
        rule = next((r for r in self.rules if r.id == item_id), None)
        if rule is None:
            return
        self._edit_rule(rule)

    def _edit_rule(self, rule: Optional[RuleConfig]) -> None:
        editing = rule is not None

        win = tk.Toplevel(self.root)
        win.title("编辑 Rule" if editing else "新建 Rule")
        win.transient(self.root)
        win.grab_set()

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="ID:").grid(row=0, column=0, sticky=tk.W, pady=4)
        id_var = tk.StringVar(value=rule.id if editing else str(uuid4()))
        ent_id = ttk.Entry(frm, textvariable=id_var, width=40)
        ent_id.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="提示词:").grid(row=1, column=0, sticky=tk.NW, pady=4)
        txt_prompt = tk.Text(frm, width=40, height=8)
        if editing and rule is not None:
            txt_prompt.insert("1.0", rule.prompt)
        txt_prompt.grid(row=1, column=1, sticky=tk.W, pady=4)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(12, 0))

        def on_ok() -> None:
            id_val = id_var.get().strip()
            if not id_val:
                messagebox.showerror("保存 Rule", "ID 不能为空。")
                return
            prompt_val = txt_prompt.get("1.0", tk.END).rstrip("\n")

            if editing and rule is not None:
                rule.id = id_val
                rule.prompt = prompt_val
            else:
                new_rule = RuleConfig(id=id_val, prompt=prompt_val)
                self.rules.append(new_rule)

            self.refresh_rules_view()
            win.destroy()

        def on_cancel() -> None:
            win.destroy()

        btn_ok = ttk.Button(btn_frame, text="保存", command=on_ok)
        btn_cancel = ttk.Button(btn_frame, text="取消", command=on_cancel)
        btn_ok.pack(side=tk.LEFT, padx=4)
        btn_cancel.pack(side=tk.LEFT, padx=4)

        win.bind("<Return>", lambda _e: on_ok())
        win.bind("<Escape>", lambda _e: on_cancel())

    def on_delete_rules(self) -> None:
        selected = list(self.tree_rules.selection())
        if not selected:
            return
        if not messagebox.askyesno("删除 Rules", f"确定要删除选中的 {len(selected)} 条 Rules 吗？"):
            return
        self.rules = [r for r in self.rules if r.id not in selected]
        self.refresh_rules_view()

    # 自动备份相关方法
    
    def load_backup_config(self) -> None:
        """加载自动备份配置"""
        config = self.auto_backup_manager.load_config()
        self.backup_interval_var.set(str(config.get("backup_interval_hours", 24)))
        self.max_backups_var.set(str(config.get("max_backups", 5)))
    
    def on_save_backup_config(self) -> None:
        """保存自动备份配置"""
        try:
            interval = int(self.backup_interval_var.get())
            max_backups = int(self.max_backups_var.get())
            
            if interval < 1 or interval > 168:
                messagebox.showerror("配置错误", "备份间隔必须在1-168小时之间。")
                return
                
            if max_backups < 1 or max_backups > 50:
                messagebox.showerror("配置错误", "最大备份数必须在1-50之间。")
                return
            
            self.auto_backup_manager.backup_interval_hours = interval
            self.auto_backup_manager.max_backups = max_backups
            self.auto_backup_manager.save_config()
            
            messagebox.showinfo("保存成功", "自动备份配置已保存。")
            self.update_backup_status()
        except ValueError:
            messagebox.showerror("配置错误", "请输入有效的数字。")
    
    def on_enable_auto_backup(self) -> None:
        """启用自动备份"""
        if not self.path_manager.get_active_path():
            messagebox.showerror("启用失败", "请先设置活动配置路径。")
            return
            
        if not self.accounts:
            messagebox.showerror("启用失败", "请先添加账号。")
            return
            
        self.auto_backup_manager.enable_auto_backup()
        self.update_backup_status()
        messagebox.showinfo("启用成功", "自动备份已启用。")
    
    def on_disable_auto_backup(self) -> None:
        """禁用自动备份"""
        self.auto_backup_manager.disable_auto_backup()
        self.update_backup_status()
        messagebox.showinfo("禁用成功", "自动备份已禁用。")
    
    def on_backup_now(self) -> None:
        """立即备份所有账号"""
        if not self.path_manager.get_active_path():
            messagebox.showerror("备份失败", "请先设置活动配置路径。")
            return
            
        if not self.accounts:
            messagebox.showerror("备份失败", "没有可备份的账号。")
            return
        
        # 创建进度对话框
        progress = tk.Toplevel(self.root)
        progress.title("备份进度")
        progress.geometry("400x150")
        progress.transient(self.root)
        progress.grab_set()
        
        ttk.Label(progress, text="正在备份账号，请稍候...").pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress, mode="indeterminate")
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        progress_bar.start()
        
        def backup_thread():
            try:
                success_count = 0
                for account in self.accounts:
                    if self.auto_backup_manager.create_backup(account.id, account.email):
                        success_count += 1
                
                progress.after(0, lambda: self._backup_complete(progress, success_count, len(self.accounts)))
            except Exception as e:
                progress.after(0, lambda: self._backup_error(progress, str(e)))
        
        import threading
        thread = threading.Thread(target=backup_thread)
        thread.daemon = True
        thread.start()
    
    def _backup_complete(self, progress: tk.Toplevel, success_count: int, total_count: int) -> None:
        """备份完成回调"""
        progress.destroy()
        self.refresh_auto_backup_view()
        messagebox.showinfo("备份完成", f"成功备份 {success_count}/{total_count} 个账号。")
    
    def _backup_error(self, progress: tk.Toplevel, error_msg: str) -> None:
        """备份错误回调"""
        progress.destroy()
        messagebox.showerror("备份失败", f"备份过程中发生错误: {error_msg}")
    
    def on_restore_backup(self) -> None:
        """恢复选中的备份"""
        selected = list(self.tree_backups.selection())
        if not selected:
            messagebox.showinfo("恢复备份", "请先选择要恢复的备份。")
            return
        
        if len(selected) > 1:
            messagebox.showinfo("恢复备份", "一次只能恢复一个备份。")
            return
        
        backup_id = selected[0]
        backups = self.auto_backup_manager.list_all_backups()
        backup = next((b for b in backups if b.get("id") == backup_id), None)
        
        if not backup:
            messagebox.showerror("恢复失败", "找不到选中的备份。")
            return
        
        account_id = backup.get("account_id")
        backup_name = backup.get("backup_name")
        account = next((a for a in self.accounts if a.id == account_id), None)
        
        if not account:
            messagebox.showerror("恢复失败", "找不到对应的账号。")
            return
        
        confirm = messagebox.askyesno(
            "确认恢复",
            f"确定要恢复以下备份吗？\n\n"
            f"账号: {account.email}\n"
            f"备份时间: {backup.get('created_at', '')}\n"
            f"备份路径: {backup.get('path', '')}\n\n"
            f"注意: 恢复操作将覆盖当前配置。"
        )
        
        if not confirm:
            return
        
        # 创建进度对话框
        progress = tk.Toplevel(self.root)
        progress.title("恢复进度")
        progress.geometry("400x150")
        progress.transient(self.root)
        progress.grab_set()
        
        ttk.Label(progress, text="正在恢复备份，请稍候...").pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress, mode="indeterminate")
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        progress_bar.start()
        
        def restore_thread():
            try:
                success = self.auto_backup_manager.restore_backup(account_id, backup_name)
                progress.after(0, lambda: self._restore_complete(progress, success, account))
            except Exception as e:
                progress.after(0, lambda: self._restore_error(progress, str(e)))
        
        import threading
        thread = threading.Thread(target=restore_thread)
        thread.daemon = True
        thread.start()
    
    def _restore_complete(self, progress: tk.Toplevel, success: bool, account: Account) -> None:
        """恢复完成回调"""
        progress.destroy()
        if success:
            messagebox.showinfo("恢复成功", f"已成功恢复账号 {account.email} 的配置备份。")
        else:
            messagebox.showerror("恢复失败", "恢复配置备份时发生错误。")
    
    def _restore_error(self, progress: tk.Toplevel, error_msg: str) -> None:
        """恢复错误回调"""
        progress.destroy()
        messagebox.showerror("恢复失败", f"恢复过程中发生错误: {error_msg}")
    
    def on_delete_backup(self) -> None:
        """删除选中的备份"""
        selected = list(self.tree_backups.selection())
        if not selected:
            messagebox.showinfo("删除备份", "请先选择要删除的备份。")
            return
        
        confirm = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(selected)} 个备份吗？\n\n"
            f"注意: 删除后无法恢复。"
        )
        
        if not confirm:
            return
        
        success_count = 0
        for backup_id in selected:
            # 从备份ID中提取账号ID和备份名称
            parts = backup_id.split("_", 1)
            if len(parts) == 2:
                account_id, backup_name = parts
                if self.auto_backup_manager.delete_backup(account_id, backup_name):
                    success_count += 1
        
        self.refresh_auto_backup_view()
        messagebox.showinfo("删除完成", f"成功删除 {success_count}/{len(selected)} 个备份。")
    
    def refresh_auto_backup_view(self) -> None:
        """刷新自动备份视图"""
        for item in self.tree_backups.get_children():
            self.tree_backups.delete(item)
        
        backups = self.auto_backup_manager.list_all_backups()
        for backup in backups:
            account_id = backup.get("account_id", "")
            account = next((a for a in self.accounts if a.id == account_id), None)
            account_email = backup.get("account_email", account.email if account else "未知账号")
            
            self.tree_backups.insert(
                "",
                tk.END,
                iid=backup.get("id", ""),
                values=(
                    account_email,
                    backup.get("created_at", ""),
                    backup.get("path", "")
                )
            )
    
    def update_backup_status(self) -> None:
        """更新备份状态显示"""
        self.backup_status_text.delete("1.0", tk.END)
        
        config = self.auto_backup_manager.load_config()
        is_enabled = self.auto_backup_manager.enabled
        interval = self.auto_backup_manager.backup_interval_hours
        max_backups = self.auto_backup_manager.max_backups
        last_backup_time = self.auto_backup_manager.last_backup_time
        
        status_text = f"自动备份状态: {'启用' if is_enabled else '禁用'}\n"
        status_text += f"备份间隔: {interval} 小时\n"
        status_text += f"最大备份数: {max_backups} 个/账号"
        
        if last_backup_time:
            status_text += f"\n上次备份: {last_backup_time}"
        
        self.backup_status_text.insert("1.0", status_text)


def run_app() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
