"""
生成数据质量报告和可视化
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


class DataQualityReport:
    """数据质量报告生成器"""
    
    def __init__(self, raw_dir: Path, cleaned_dir: Path, output_dir: Path):
        """
        初始化报告生成器
        
        Args:
            raw_dir: 原始数据目录
            cleaned_dir: 清洗后数据目录
            output_dir: 报告输出目录
        """
        self.raw_dir = raw_dir
        self.cleaned_dir = cleaned_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.cities = ['北京', '成都', '广州', '杭州', '上海', '深圳']
        self.stats = {}
    
    def generate_full_report(self):
        """生成完整报告"""
        print("=== 开始生成数据质量报告 ===\n")
        
        # 1. 收集统计数据
        self._collect_statistics()
        
        # 2. 生成文本报告
        self._generate_text_report()
        
        # 3. 生成可视化图表
        self._generate_visualizations()
        
        # 4. 生成HTML报告
        self._generate_html_report()
        
        print(f"\n报告生成完成！保存在: {self.output_dir}")
    
    def _collect_statistics(self):
        """收集统计数据"""
        print("收集统计数据...")
        
        for city in self.cities:
            city_stats = {
                'city': city,
                'raw': {},
                'cleaned': {},
                'skills': {}
            }
            
            # 原始数据统计
            raw_file = self.raw_dir / f'boss_{city}.json'
            if raw_file.exists():
                with open(raw_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    city_stats['raw'] = self._analyze_data(raw_data)
            
            # 清洗后数据统计
            cleaned_file = self.cleaned_dir / f'boss_{city}_cleaned.json'
            if cleaned_file.exists():
                with open(cleaned_file, 'r', encoding='utf-8') as f:
                    cleaned_data = json.load(f)
                    city_stats['cleaned'] = self._analyze_data(cleaned_data)
                    city_stats['skills'] = self._analyze_skills(cleaned_data)
            
            self.stats[city] = city_stats
        
        # 汇总统计
        self.stats['summary'] = self._calculate_summary()
    
    def _analyze_data(self, data: list) -> dict:
        """分析数据集"""
        if not data:
            return {}
        
        stats = {
            'total': len(data),
            'with_skills': sum(1 for j in data if j.get('skills') and len(j['skills']) > 0),
            'education_dist': Counter(j.get('education', '未知') for j in data),
            'experience_dist': Counter(j.get('experience', '未知') for j in data),
            'salary_range': self._get_salary_range(data),
            'top_companies': Counter(j.get('company', '未知') for j in data).most_common(10)
        }
        
        return stats
    
    def _analyze_skills(self, data: list) -> dict:
        """分析技能分布"""
        all_skills = []
        for job in data:
            skills = job.get('skills', [])
            if skills:
                all_skills.extend(skills)
        
        skill_counter = Counter(all_skills)
        
        return {
            'total_skills': len(skill_counter),
            'top_skills': skill_counter.most_common(30),
            'avg_skills_per_job': len(all_skills) / len(data) if data else 0
        }
    
    def _get_salary_range(self, data: list) -> dict:
        """获取薪资范围统计"""
        salaries = []
        for job in data:
            salary_min = job.get('salary_min', 0)
            salary_max = job.get('salary_max', 0)
            if 0 < salary_min < salary_max <= 200:
                salaries.append((salary_min, salary_max))
        
        if not salaries:
            return {}
        
        min_salaries = [s[0] for s in salaries]
        max_salaries = [s[1] for s in salaries]
        
        return {
            'min': min(min_salaries),
            'max': max(max_salaries),
            'avg_min': sum(min_salaries) / len(min_salaries),
            'avg_max': sum(max_salaries) / len(max_salaries),
            'median_min': sorted(min_salaries)[len(min_salaries)//2],
            'median_max': sorted(max_salaries)[len(max_salaries)//2]
        }
    
    def _calculate_summary(self) -> dict:
        """计算汇总统计"""
        total_raw = sum(self.stats[city]['raw'].get('total', 0) for city in self.cities)
        total_cleaned = sum(self.stats[city]['cleaned'].get('total', 0) for city in self.cities)
        
        # 汇总所有技能
        all_skills_count = Counter()
        for city in self.cities:
            skills_data = self.stats[city]['skills']
            if skills_data and 'top_skills' in skills_data:
                for skill, count in skills_data['top_skills']:
                    all_skills_count[skill] += count
        
        return {
            'total_raw': total_raw,
            'total_cleaned': total_cleaned,
            'retention_rate': total_cleaned / total_raw if total_raw > 0 else 0,
            'total_cities': len(self.cities),
            'top_skills_overall': all_skills_count.most_common(50)
        }
    
    def _generate_text_report(self):
        """生成文本报告"""
        print("生成文本报告...")
        
        report_file = self.output_dir / 'data_quality_report.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("智能招聘信息聚合分析系统 - 数据质量报告\n")
            f.write("="*80 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 汇总统计
            summary = self.stats['summary']
            f.write("一、数据汇总\n")
            f.write("-"*80 + "\n")
            f.write(f"城市数量: {summary['total_cities']}\n")
            f.write(f"原始数据总量: {summary['total_raw']:,} 条\n")
            f.write(f"清洗后数据量: {summary['total_cleaned']:,} 条\n")
            f.write(f"数据保留率: {summary['retention_rate']*100:.2f}%\n\n")
            
            # 分城市统计
            f.write("二、分城市统计\n")
            f.write("-"*80 + "\n")
            for city in self.cities:
                city_data = self.stats[city]
                raw_total = city_data['raw'].get('total', 0)
                cleaned_total = city_data['cleaned'].get('total', 0)
                retention = (cleaned_total / raw_total * 100) if raw_total > 0 else 0
                
                f.write(f"\n{city}:\n")
                f.write(f"  原始数据: {raw_total:,} 条\n")
                f.write(f"  清洗后: {cleaned_total:,} 条\n")
                f.write(f"  保留率: {retention:.2f}%\n")
                
                # 薪资统计
                salary_range = city_data['cleaned'].get('salary_range', {})
                if salary_range:
                    f.write(f"  薪资范围: {salary_range['min']:.0f}K - {salary_range['max']:.0f}K\n")
                    f.write(f"  平均薪资: {salary_range['avg_min']:.1f}K - {salary_range['avg_max']:.1f}K\n")
            
            # TOP技能
            f.write("\n\n三、热门技能排行（TOP 30）\n")
            f.write("-"*80 + "\n")
            for i, (skill, count) in enumerate(summary['top_skills_overall'][:30], 1):
                f.write(f"{i:2d}. {skill:20s} - {count:,} 次\n")
            
            # 学历和经验分布（以北京为例）
            if '北京' in self.stats:
                bj_data = self.stats['北京']['cleaned']
                f.write("\n\n四、学历要求分布（以北京为例）\n")
                f.write("-"*80 + "\n")
                for edu, count in bj_data['education_dist'].most_common(10):
                    pct = count / bj_data['total'] * 100
                    f.write(f"  {edu:10s}: {count:,} ({pct:.1f}%)\n")
                
                f.write("\n五、经验要求分布（以北京为例）\n")
                f.write("-"*80 + "\n")
                for exp, count in bj_data['experience_dist'].most_common(10):
                    pct = count / bj_data['total'] * 100
                    f.write(f"  {exp:15s}: {count:,} ({pct:.1f}%)\n")
        
        print(f"文本报告已保存: {report_file}")
    
    def _generate_visualizations(self):
        """生成可视化图表"""
        print("生成可视化图表...")
        
        # 1. 城市数据量对比
        self._plot_city_comparison()
        
        # 2. TOP技能排行
        self._plot_top_skills()
        
        # 3. 薪资分布
        self._plot_salary_distribution()
        
        # 4. 学历和经验分布
        self._plot_education_experience()
    
    def _plot_city_comparison(self):
        """绘制城市数据量对比图"""
        cities = self.cities
        raw_counts = [self.stats[city]['raw'].get('total', 0) for city in cities]
        cleaned_counts = [self.stats[city]['cleaned'].get('total', 0) for city in cities]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = range(len(cities))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], raw_counts, width, label='原始数据', alpha=0.8)
        ax.bar([i + width/2 for i in x], cleaned_counts, width, label='清洗后', alpha=0.8)
        
        ax.set_xlabel('城市', fontsize=12)
        ax.set_ylabel('数据量', fontsize=12)
        ax.set_title('各城市招聘数据量对比', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(cities)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 添加数值标签
        for i, (raw, cleaned) in enumerate(zip(raw_counts, cleaned_counts)):
            ax.text(i - width/2, raw, f'{raw:,}', ha='center', va='bottom', fontsize=9)
            ax.text(i + width/2, cleaned, f'{cleaned:,}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'city_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"城市对比图已保存")
    
    def _plot_top_skills(self):
        """绘制TOP技能排行"""
        summary = self.stats['summary']
        top_skills = summary['top_skills_overall'][:20]
        
        if not top_skills:
            return
        
        skills = [s[0] for s in top_skills]
        counts = [s[1] for s in top_skills]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        y_pos = range(len(skills))
        colors = plt.cm.viridis([i/len(skills) for i in range(len(skills))])
        
        ax.barh(y_pos, counts, color=colors, alpha=0.8)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(skills)
        ax.invert_yaxis()
        ax.set_xlabel('需求数量', fontsize=12)
        ax.set_title('热门技能需求排行 TOP 20', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        
        # 添加数值标签
        for i, count in enumerate(counts):
            ax.text(count, i, f'  {count:,}', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'top_skills.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"TOP技能图已保存")
    
    def _plot_salary_distribution(self):
        """绘制薪资分布图"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('各城市薪资分布', fontsize=16, fontweight='bold')
        
        for idx, city in enumerate(self.cities):
            ax = axes[idx // 3][idx % 3]
            
            salary_range = self.stats[city]['cleaned'].get('salary_range', {})
            if salary_range:
                categories = ['最低', '平均最低', '中位最低', '中位最高', '平均最高', '最高']
                values = [
                    salary_range['min'],
                    salary_range['avg_min'],
                    salary_range['median_min'],
                    salary_range['median_max'],
                    salary_range['avg_max'],
                    salary_range['max']
                ]
                
                colors = ['#ff9999', '#ffcc99', '#ffff99', '#99ff99', '#99ccff', '#cc99ff']
                ax.bar(range(len(categories)), values, color=colors, alpha=0.7)
                ax.set_xticks(range(len(categories)))
                ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
                ax.set_ylabel('薪资 (K)', fontsize=10)
                ax.set_title(city, fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3, axis='y')
                
                # 添加数值标签
                for i, val in enumerate(values):
                    ax.text(i, val, f'{val:.0f}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'salary_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"薪资分布图已保存")
    
    def _plot_education_experience(self):
        """绘制学历和经验分布"""
        # 以北京数据为例
        if '北京' not in self.stats:
            return
        
        bj_data = self.stats['北京']['cleaned']
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('学历与经验要求分布（北京）', fontsize=14, fontweight='bold')
        
        # 学历分布
        edu_data = bj_data['education_dist'].most_common(6)
        if edu_data:
            labels = [e[0] for e in edu_data]
            sizes = [e[1] for e in edu_data]
            colors = plt.cm.Set3(range(len(labels)))
            
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
            ax1.set_title('学历要求分布', fontsize=12)
        
        # 经验分布
        exp_data = bj_data['experience_dist'].most_common(8)
        if exp_data:
            labels = [e[0] for e in exp_data]
            sizes = [e[1] for e in exp_data]
            
            ax2.barh(range(len(labels)), sizes, color=plt.cm.Pastel1(range(len(labels))))
            ax2.set_yticks(range(len(labels)))
            ax2.set_yticklabels(labels)
            ax2.invert_yaxis()
            ax2.set_xlabel('岗位数量', fontsize=10)
            ax2.set_title('经验要求分布', fontsize=12)
            ax2.grid(True, alpha=0.3, axis='x')
            
            # 添加数值标签
            for i, size in enumerate(sizes):
                ax2.text(size, i, f'  {size:,}', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'education_experience.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"学历经验分布图已保存")
    
    def _generate_html_report(self):
        """生成HTML报告"""
        print("生成HTML报告...")
        
        summary = self.stats['summary']
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据质量报告 - 智能招聘信息聚合分析系统</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }}
        .chart-container {{
            margin: 30px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 数据质量报告</h1>
        <p style="color: #7f8c8d;">生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        
        <h2>一、数据概览</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>城市数量</h3>
                <p class="value">{summary['total_cities']}</p>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h3>原始数据总量</h3>
                <p class="value">{summary['total_raw']:,}</p>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <h3>清洗后数据量</h3>
                <p class="value">{summary['total_cleaned']:,}</p>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <h3>数据保留率</h3>
                <p class="value">{summary['retention_rate']*100:.1f}%</p>
            </div>
        </div>
        
        <h2>二、城市数据对比</h2>
        <div class="chart-container">
            <img src="city_comparison.png" alt="城市数据对比">
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>城市</th>
                    <th>原始数据</th>
                    <th>清洗后</th>
                    <th>保留率</th>
                    <th>平均薪资范围</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for city in self.cities:
            city_data = self.stats[city]
            raw_total = city_data['raw'].get('total', 0)
            cleaned_total = city_data['cleaned'].get('total', 0)
            retention = (cleaned_total / raw_total * 100) if raw_total > 0 else 0
            
            salary_range = city_data['cleaned'].get('salary_range', {})
            salary_text = ''
            if salary_range:
                salary_text = f"{salary_range['avg_min']:.1f}K - {salary_range['avg_max']:.1f}K"
            
            html_content += f"""
                <tr>
                    <td><strong>{city}</strong></td>
                    <td>{raw_total:,}</td>
                    <td>{cleaned_total:,}</td>
                    <td>{retention:.2f}%</td>
                    <td>{salary_text}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
        
        <h2>三、热门技能分析</h2>
        <div class="chart-container">
            <img src="top_skills.png" alt="热门技能排行">
        </div>
        
        <h2>四、薪资分布</h2>
        <div class="chart-container">
            <img src="salary_distribution.png" alt="薪资分布">
        </div>
        
        <h2>五、学历与经验要求</h2>
        <div class="chart-container">
            <img src="education_experience.png" alt="学历经验分布">
        </div>
        
        <div class="footer">
            <p>© 2025 基于技能图谱的智能招聘信息聚合分析系统</p>
            <p>毕业设计项目 | 智能科学与技术专业</p>
        </div>
    </div>
</body>
</html>
"""
        
        html_file = self.output_dir / 'data_quality_report.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML报告已保存: {html_file}")


if __name__ == '__main__':
    # 配置路径
    raw_dir = project_root / 'data' / 'raw'
    cleaned_dir = project_root / 'data' / 'cleaned'
    output_dir = project_root / 'reports'
    
    # 生成报告
    reporter = DataQualityReport(raw_dir, cleaned_dir, output_dir)
    reporter.generate_full_report()
    
    print("\n✅ 所有报告生成完成！")
    print(f"📁 报告目录: {output_dir}")
    print(f"📄 文本报告: data_quality_report.txt")
    print(f"🌐 HTML报告: data_quality_report.html")
    print(f"📊 图表文件: city_comparison.png, top_skills.png, 等")
