"""
数据质量分析脚本
"""
import json
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def analyze_data_quality():
    """分析招聘数据质量"""
    
    cities = ['北京', '成都', '广州', '杭州', '上海', '深圳']
    data_dir = project_root / 'data' / 'raw'
    
    total_stats = {
        'total_jobs': 0,
        'empty_skills': 0,
        'empty_education': 0,
        'empty_experience': 0,
        'salary_issues': 0,
        'valid_jobs': 0,
        'city_stats': {}
    }
    
    print("=== 分城市统计 ===")
    for city in cities:
        file_path = data_dir / f'boss_{city}.json'
        if not file_path.exists():
            print(f'{city}: 文件不存在')
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        city_count = len(data)
        city_valid = 0
        city_empty_skills = 0
        city_salary_issues = 0
        
        for job in data:
            # 检查skills字段
            has_skills = job.get('skills') and len(job.get('skills', [])) > 0
            if not has_skills:
                total_stats['empty_skills'] += 1
                city_empty_skills += 1
            
            # 检查education
            if not job.get('education') or job.get('education') == '':
                total_stats['empty_education'] += 1
            
            # 检查experience
            if not job.get('experience') or job.get('experience') == '':
                total_stats['empty_experience'] += 1
            
            # 检查薪资异常
            salary_min = job.get('salary_min', 0)
            salary_max = job.get('salary_max', 0)
            salary_valid = True
            
            if salary_min <= 0 or salary_max <= 0:
                salary_valid = False
            elif salary_max < salary_min:
                salary_valid = False
            elif salary_max > 200 or salary_min > 150:
                salary_valid = False
            
            if not salary_valid:
                total_stats['salary_issues'] += 1
                city_salary_issues += 1
            
            # 统计有效岗位（skills不为空且薪资正常）
            if has_skills and salary_valid:
                total_stats['valid_jobs'] += 1
                city_valid += 1
        
        total_stats['total_jobs'] += city_count
        total_stats['city_stats'][city] = {
            'total': city_count,
            'valid': city_valid,
            'empty_skills': city_empty_skills,
            'salary_issues': city_salary_issues,
            'valid_rate': f"{city_valid/city_count*100:.2f}%"
        }
        
        print(f'{city}: {city_count:,} 条，有效: {city_valid:,} ({city_valid/city_count*100:.2f}%)')
    
    print(f'\n=== 整体数据质量统计 ===')
    print(f'总岗位数: {total_stats["total_jobs"]:,}')
    print(f'skills为空: {total_stats["empty_skills"]:,} ({total_stats["empty_skills"]/total_stats["total_jobs"]*100:.2f}%)')
    print(f'education为空: {total_stats["empty_education"]:,} ({total_stats["empty_education"]/total_stats["total_jobs"]*100:.2f}%)')
    print(f'experience为空: {total_stats["empty_experience"]:,} ({total_stats["empty_experience"]/total_stats["total_jobs"]*100:.2f}%)')
    print(f'薪资异常: {total_stats["salary_issues"]:,} ({total_stats["salary_issues"]/total_stats["total_jobs"]*100:.2f}%)')
    print(f'有效岗位: {total_stats["valid_jobs"]:,} ({total_stats["valid_jobs"]/total_stats["total_jobs"]*100:.2f}%)')
    
    # 采样分析
    print(f'\n=== 数据样本分析 ===')
    sample_file = data_dir / 'boss_北京.json'
    with open(sample_file, 'r', encoding='utf-8') as f:
        sample_data = json.load(f)
    
    # 分析前10条有skills的数据
    print("\n前5条有skills的岗位示例：")
    count = 0
    for job in sample_data:
        if job.get('skills') and len(job['skills']) > 0:
            count += 1
            print(f"\n{count}. {job['title']} - {job['company']}")
            print(f"   薪资: {job['salary_text']}")
            print(f"   技能: {', '.join(job['skills'])}")
            print(f"   学历: {job.get('education', '未知')} | 经验: {job.get('experience', '未知')}")
            if count >= 5:
                break
    
    # 分析薪资分布
    print("\n=== 薪资分布分析（北京） ===")
    salaries = []
    for job in sample_data:
        salary_min = job.get('salary_min', 0)
        salary_max = job.get('salary_max', 0)
        if 0 < salary_min < salary_max <= 200:
            salaries.append((salary_min, salary_max))
    
    if salaries:
        min_salaries = [s[0] for s in salaries]
        max_salaries = [s[1] for s in salaries]
        
        print(f"最低薪资范围: {min(min_salaries)}K - {max(min_salaries)}K")
        print(f"最高薪资范围: {min(max_salaries)}K - {max(max_salaries)}K")
        print(f"平均薪资范围: {sum(min_salaries)/len(min_salaries):.1f}K - {sum(max_salaries)/len(max_salaries):.1f}K")
    
    return total_stats


if __name__ == '__main__':
    analyze_data_quality()
