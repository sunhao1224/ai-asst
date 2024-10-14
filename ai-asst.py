from datetime import datetime
import random
import re
from flask import Flask, request, jsonify
from dataclasses import dataclass, field, asdict, fields, is_dataclass
from typing import List, Dict, Type
import json
from time import sleep, time
from zhipuai import ZhipuAI
from json_tool import try_parse_ast_to_json, try_parse_json_object
import logging

from flask_cors import CORS

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources=r'/*')
client = ZhipuAI(api_key="d0ec437e4b38610fe6a811eff802da77.pcTnm7mFo2Ue30Lm") 

# 定义转换函数
def dataclass_from_dict(klass: Type, data: Dict) -> any:
    if hasattr(klass, "__annotations__"):  # 检查是否为dataclass
        fieldtypes = klass.__annotations__
        return klass(**{f: dataclass_from_dict(fieldtypes[f], data[f]) for f in data})
    elif isinstance(data, (list, tuple)):
        return [dataclass_from_dict(klass.__args__[0], d) for d in data]  # 处理列表中的元素
    else:
        return data  # 基本类型直接返回

# def dataclass_to_dict(instance) -> Dict:
#     if hasattr(instance, "to_dict"):
#         return instance.to_dict()
#     elif isinstance(instance, list):
#         return [dataclass_to_dict(item) for item in instance]
#     elif isinstance(instance, dict):
#         return {k: dataclass_to_dict(v) for k, v in instance.items()}
#     else:
#         try:
#             return asdict(instance)
#         except TypeError:
#             return instance


def dataclass_to_dict(instance) -> Dict:
    if hasattr(instance, "to_dict"):
        return instance.to_dict()
    elif isinstance(instance, list):
        return [dataclass_to_dict(item) for item in instance]
    elif isinstance(instance, dict):
        return {k: dataclass_to_dict(v) for k, v in instance.items()}
    elif is_dataclass(instance):
        return {f.name: dataclass_to_dict(getattr(instance, f.name)) for f in fields(instance)}
    else:
        return instance

@dataclass
class Dimension:
    # 维度名称
    dimension_name: str = ""
    # 一级指标
    first_level_index: str = ""
    # 二级指标
    second_level_index: str = ""
    # 核心字段召回
    core_field_recall: str = ""

@dataclass
class ScoreKeyPoint:
    # 学生姓名
    stu_name: str = ""
    # 学生学号
    stu_id: int = ""
    # 单个答题要点名称
    single_answer_key_point_name: str = ""
    # 单个答题要点得分
    single_answer_key_point_score: float = 0.0

@dataclass
class StudentAnswer:
    # 学生姓名
    stu_name: str = ""
    # 学生学号
    stu_id: int = ""
    # 学生答案
    stu_answer: str = ""
    # 老师评分，小数类型
    teacher_score: float = 0.0
    # 根据老师评分的排名
    teacher_score_rank: int = 0
    # 老师评分理由
    teacher_score_reason: str = ""
    # ai评分
    ai_score: float = 0.0
    # ai评分理由
    ai_score_reason: str = ""
    # 学生评分等级,A,B,C,D,E
    stu_score_level: str = ""
    # ai评分标签，str列表
    ai_score_tags: List[str] = field(default_factory=list)
    # 学生答案命中得分要点的个数
    hit_view_count: int = 0
    # 学生答案命中得分要点列表
    hit_view_list: List[str] = field(default_factory=list)
    # 学生答案命中得分要点的符合度列表
    stu_answer_score_key_points_match_list: List[float] = field(default_factory=list)
    # 学生答案疑似AI生成可疑度
    stu_answer_ai_suspicious: float = 0.0
    # 学生答案疑似AI生成可疑理由
    stu_answer_ai_suspicious_reason: str = ""
    # 学生答案疑似抄袭可疑度
    stu_answer_plagiarism_suspicious: float = 0.0
    # 学生答案疑似抄袭可疑理由
    stu_answer_plagiarism_suspicious_reason: str = ""
    # 学生答案主旨词
    # stu_answer_main_idea: str = ""
    stu_characteristics: str = ""
    # ai阅卷状态
    ai_status: bool = False
    # 答题时间,默认值为当前日期时间
    answer_time: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 学生观点凝练
    stu_view_clarify: str = ""
    # 学生答案优化
    stu_answer_optimization: str = ""
    
@dataclass
class Question:
    # 老师姓名
    teacher_name: str = ""
    # 考试编号
    exam_id: str = ""
    # 考试名称
    exam_name: str = ""
    # 考试时间
    exam_time: str = ""
    # 考试科目
    exam_subject: str = ""
    # 考题内容
    question_content: str = ""
    # ai prompt
    ai_prompt: str = ""
    # 标准答案，用于和用户答案进行对比
    standard_answer: str = ""
    # ai答案
    ai_answer: str = ""
    # 题目难度分析
    question_difficulty: str  = ""
    # 得分要点列表
    score_key_points: List[str] = field(default_factory=list)
    # 得分要点列表数字
    score_key_points_num: List[str] = field(default_factory=list)
    # 每个得分要点人数统计
    score_key_hit_points_count: List[int] = field(default_factory=list)
    score_key_miss_points_count: List[int] = field(default_factory=list)
    # 每个得分要点的学生排名表格，是一个二维列表，列表元素是StudentAnswer
    # 得分要点1，对应score_key_points_rank[0]
    score_key_points_rank: List[List[ScoreKeyPoint]] = field(default_factory=list)
    # 考试维度列表, 类型为Dimension
    exam_dimension_list: List[Dimension] = field(default_factory=list)
    # 学生答案列表，类型为StudentAnswer
    stu_answer_list: List[StudentAnswer] = field(default_factory=list)
    # 考题得分等级
    score_level_labels : List[str] = field(default_factory=list)
    # 考题得分等级人数,A\B\C\D\E
    score_level_count: List[int] = field(default_factory=list)
    # ai标签人数,{"完美试卷": 1,"高分试卷": 1,"疑似AI":1,"雷同试卷":1,"疑似抄袭":1},
    ai_tag_list: List[str] = field(default_factory=list)
    ai_tag_count: List[int] = field(default_factory=list)
    # 主旨词列表
    main_word_list: List[str] = field(default_factory=list)
    # 主旨词分布统计
    main_word_distribution_count: List[int] = field(default_factory=list)

@dataclass
class Test:
    # 考试名称
    name: str = ""
    # 考题，字典类型为str:Question
    questions: Dict[int, Question] = field(default_factory=dict)

# __question_content=""
# __standard_answer=""
# system_prompt_give_dimension=""
# user_prompt_give_dimension=""
# __score_key_points=""
# __stu_answer=""
# __dimsnsions=""
# __core_field_recalls=""

# 定义Test类型的实例，其中questions为空字典
test = Test(name="Midterm Exam", questions={})

# 定义一个函数，参数为questions的key和json格式的字符串，将json字符串转换为Question类型，并添加到test的questions字典中
def add_question(key: int, json_str: str):
    json_str,json_dict=try_parse_json_object(json_str)
    test.questions[key] = dataclass_from_dict(Question, json_dict)

# 假设Test实例已经创建，并且add_question函数也已定义
test = Test(name="Midterm Exam", questions={})

def GLM4_FUNCTION(system_prompt: str, user_prompt: str):
    assert(system_prompt!="")
    assert(user_prompt!="")
    try:
        chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=chat_history,
            stream=True
        )
        # 获取模型的回答
        model_response = ""
        # 打印模型回答
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                chunk_content = chunk.choices[0].delta.content
                model_response += chunk_content
        # print(model_response)
        return model_response
    except Exception as e:
        print(f"Error in GLM4_FUNCTION: {e}")
        return ""

# 自定义JSON序列化
class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        json_str = super().encode(obj)
        return json_str.replace(r'\\n', '\n')

app.json_encoder = CustomJSONEncoder

@app.route('/add_question', methods=['POST'])
def add_question_route():
    json_str = request.json
    key=json_str.get('id')
    key=int(key)
    question=json_str.get('question')
    # question to str
    question = json.dumps(question)
    try:
        add_question(key, question)
        return jsonify({"success": True, "message": "Question added successfully."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route('/update_question_content_standard_answer', methods=['POST'])
def update_question_content_standard_answer_route():
    id = request.form['id']
    question_content = request.form['question_content']
    standard_answer = request.form['standard_answer']
    id=int(id)
    # 创建Question类实例,只设置question_content和standard_answer，其他属性设为默认值
    
    print("update:",id,question_content,standard_answer)
    question = Question(question_content=question_content, standard_answer=standard_answer)    
    # 如果key不存在test.questions的key中，则创建键值对
    if id not in test.questions.keys():
        test.questions[id] = question
        # print("create:",test.questions[id])
    test.questions[id].question_content = question_content
    test.questions[id].standard_answer = standard_answer
    return jsonify({"success": True, "message": "Question added successfully."}), 200

@app.route('/get_question', methods=['GET'])
def get_question():
    id = request.args.get('id')
    # id转为int
    id = int(id)
    # 使用dataclass_to_dict函数转换Question实例为字典
    question_dict = dataclass_to_dict(test.questions[id])
    # 转换为JSON字符串
    # question_json = json.dumps(question_dict, indent=4, ensure_ascii=False)
    # print(question_json)
    return jsonify(question_dict), 200

@app.route('/get_all_questions', methods=['GET'])
def get_all_questions_route():
    # test.questions 转为字典列表
    questions_list = [dataclass_to_dict(question) for question in test.questions.values()]
    # questions_list转换为JSON字符串
    # questions_json = json.dumps(questions_list, indent=4, ensure_ascii=False)
    # print(questions_json)
    return jsonify(questions_list), 200

def gen_score_key_points(id: int ,question_content: str, standard_answer: str):
    system_prompt_give_dimension=f"""
##【任务要求】
根据【考题内容】和【标准答案】，生成考题的得分点

##【字段定义】：
请严格按照如下格式仅输出JSON，不要输出python代码，不要返回多余信息，JSON中有多个字段用顿号【、】区隔：
### JSON字段：
{{
    "score_key_points": ["得分点内容"]
}}
"""

    user_prompt_give_dimension=f"""
##【考题内容】
{question_content}

##【标准答案】
{standard_answer}    
"""
    json_str=GLM4_FUNCTION(system_prompt=system_prompt_give_dimension, user_prompt=user_prompt_give_dimension)
    json_str,json_dict=try_parse_json_object(json_str)
    # json_data=json.loads(json_str)
    test.questions[id].score_key_points= json_dict['score_key_points']

@app.route('/add_dimension', methods=['POST'])
def add_dimension():
    id = request.form['id']
    id=int(id)
    dimension_name = request.form['dimension_name']
    first_level_index = request.form['first_level_index']
    second_level_index = request.form['second_level_index']
    core_field_recall = request.form['core_field_recall']

    # 添加维度
    test.questions[id].exam_dimension_list.append(
        Dimension(
            dimension_name=dimension_name,
            first_level_index=first_level_index,
            second_level_index=second_level_index,
            core_field_recall=core_field_recall
        )
    )
    
    return jsonify({"success": True, "message": "Question added successfully."}), 200

@app.route('/get_dimension', methods=['GET'])
def get_dimension_route():
    id = request.args.get('id')
    id=int(id)
    question_dict = dataclass_to_dict(test.questions[id])
    return jsonify(question_dict), 200


@app.route('/give_dimension', methods=['GET'])
def give_dimension_route():

    id = request.args.get('id')
    # id转为int
    id = int(id)
    __standard_answer=test.questions[id].standard_answer
    __question_content=test.questions[id].question_content
    system_prompt_give_dimension=f"""
##【任务要求】
根据【题目】和【参考答案】，给出对应的(维度,一级指标,二级指标,核心字段召回)JSON列表，列表长度不能大于6。
1. 维度名称【dimension_name】： 维度是指评价或测试的某个方面或领域。它是评价内容的分类方式，用于确定评价的方向和重点。例如，在一份学生的综合评价中，可能包含“知识掌握”、“技能应用”和“情感态度”等维度。
2. 一级指标【first_level_index】： 一级指标是维度的进一步细分，它描述了需要考虑的主要因素，不能给出具体实例。一级指标通常是评价体系中的主要评判点，例如在“知识掌握”维度下，一级指标可能是“基础知识掌握”、“专业知识掌握”等。
3. 二级指标【second_level_index】： 二级指标是对一级指标的进一步细化，它描述了如何具体评价一级指标。二级指标通常是可量化的具体评价点，例如在“基础知识掌握”一级指标下，二级指标可能是“记忆准确度”、“理解深度”等。
4. 核心字段召回【core_field_recall】： 不超过6个字。核心字段召回指的是在评价过程中需要特别关注和记录的关键信息或数据点。这些字段是评价结果的关键组成部分，它们直接关联到评价对象在该指标上的表现。例如，如果评价学生的“记忆准确度”，核心字段召回可能是学生在记忆测试中的正确率。

##【字段定义】：
请严格按照如下格式仅输出JSON，不要输出python代码，不要返回多余信息，JSON中有多个字段用顿号【、】区隔：
### JSON字段：
{{
"exam_dimension_list":[
    {{
        "dimension_name": "【任务要求】1. 维度名称",
        "first_level_index": "【任务要求】2. 一级指标",
        "second_level_index": "【任务要求】3. 二级指标",
        "core_field_recall": "【任务要求】4. 核心字段召回"
    }},
    ...
]
}}

## 注意事项：
1. 基于给出的内容，专业和严谨的回答问题。不允许添加任何编造成分。
"""
    user_prompt_give_dimension=f"""
##【题目】：
{__question_content}

##【参考答案】：
{__standard_answer}
"""

    json_str=GLM4_FUNCTION(system_prompt_give_dimension, user_prompt_give_dimension)
    # print(system_prompt_give_dimension)
    # print(user_prompt_give_dimension)
    # 解析JSON字符串
    json_str,json_dict=try_parse_json_object(json_str)

    # json_data_dict = json.loads(json_str)
    # 转换JSON数据中的每个项为Dimension对象
    new_exam_dimensions = [dataclass_from_dict(Dimension,item) for item in json_dict['exam_dimension_list']]
    # 更新test_instance中question[1]的exam_dimension_list
    test.questions[id].exam_dimension_list = new_exam_dimensions
    question_dict = dataclass_to_dict(test.questions[id])
    return jsonify(question_dict), 200

@app.route('/get_ai_prompt', methods=['GET'])
def get_ai_prompt_route():
    # global __question_content,__standard_answer,__score_key_points,__stu_answer,__dimsnsions,__core_field_recalls,system_prompt_give_dimension,user_prompt_give_dimension
    __question_content=""
    __standard_answer=""
    __score_key_points=""
    __dimsnsions=""
    __core_field_recalls=""
    __score_history=""

    id = request.args.get('id')
    # id转为int
    id = int(id)
    question_dict = dataclass_to_dict(test.questions[id])

    # 如果key不存在test.questions的key中，则创建键值对
    if id not in test.questions.keys():
        test.questions[id] = dataclass_from_dict(Question, question_dict)
    # 获取维度元素列表
    exam_dimension_list = dataclass_from_dict(Question, question_dict).exam_dimension_list
    #打印维度字符串列表
    for dimension in exam_dimension_list:
        __dimsnsions += f"({dimension.dimension_name}, {dimension.first_level_index}, {dimension.second_level_index})"
    # 获取核心字段列表
    unique_core_fields = set()
    for dim in exam_dimension_list:
        if dim.core_field_recall:
            unique_core_fields.add(dim.core_field_recall)
    # 将结果组合成一个字符串
    __core_field_recalls = ",".join(unique_core_fields)
    __core_field_recalls="{"+__core_field_recalls+"}"

    __question_content=dataclass_from_dict(Question, question_dict).question_content
    __standard_answer=dataclass_from_dict(Question, question_dict).standard_answer
    
    gen_score_key_points(id,__question_content,__standard_answer)
    score_key_points=test.questions[id].score_key_points
    score_key_points_string = ", ".join(score_key_points)
    score_key_points_string = "{"+score_key_points_string+"}"
    __score_key_points=score_key_points_string

    system_prompt_give_dimension=f"""
## 角色：你是一个专业的课程老师 ，现在需要你批改试题，我将发给你学生答案，需要你按照以下【任务要求】执行。

##【打分历史记录】
{__score_history}


## 【评分规则】：
1. 总分为100分。
2. 如果【打分历史记录】中有内容，学习【打分历史记录】，根据其中的 老师评论、老师打分 情况进行打分。
3. 【学生答案】需要围绕【维度和指标】内容以及【参考答案】展开，必须包含的核心字段有：{__core_field_recalls}。越贴近得分越多，越远离扣分越多。
4. 参考答案中的关键名字不能写错，写错需要扣分。每个人评分不能相同。不能给85分。

##【维度和指标】：元素格式为(维度,一级指标,二级指标）
{__dimsnsions}

## 考题内容：
{__question_content}

##【参考答案】：
{__standard_answer}

## 得分要点列表：
{__score_key_points}

## 【任务要求】：
1. ai_score: AI 评分。根据【评分规则】评分，最高得分不能超过100分，最低分为0分。评分的依据在【ai_score_reason】项中给出。
2. ai_score_reason: AI 评分依据。每道题目的评分原因的内容不能超过100字。
3. ai_score_tags: AI 评分标签列表。分别是："完美试卷"、"高分试卷"、"疑似AI"。其中"高分试卷"的给出依据是得分【ai_score】在90分以上，"疑似AI"的给出依据是学生答案疑似AI生成可疑度【stu_answer_ai_suspicious】大于80%，"完美试卷"的给出依据是【ai_score】在90分以上且学生答案疑似AI生成可疑度【stu_answer_ai_suspicious】小于10%。
4. ai_answer: AI 答案。AI 答案不超过300字，AI 答案需要根据【考题内容】和【参考答案】给出。
5. hit_view_list: 学生答案命中得分要点列表。学生答案的要点与符合【得分要点列表】的交集。元素的个数等于【hit_view_count】
6. stu_answer_score_key_points_match_list: 学生答案命中得分要点的符合度列表。【hit_view_list】中每个要点的符合度，每个元素的类型为百分数，取值越大表示学生答案与得分要点的匹配程度越高。元素的个数等于【hit_view_count】
7. hit_view_count: 学生答案命中得分要点的个数。【hit_view_list】中元素的个数。
8. stu_answer_ai_suspicious: 学生答案疑似AI生成可疑度。表示学生答案疑似AI生成的概率，根据【stu_answer_ai_suspicious_reason】给出概率。类型为百分数。
9. stu_answer_ai_suspicious_reason: 学生答案疑似AI的原因。不超过200字。可以通过以下几个方面进行分析：
    - 语言风格分析：AI 生成的内容可能在语言风格上过于统一，缺乏个性和情感色彩。可以通过对比内容中的语言风格，判断是否与人类的自然表达方式一致。
    - 逻辑一致性：AI 在生成内容时，可能会在某些地方出现逻辑跳跃或不够连贯的表达。可以通过逻辑分析，检查文本中的论述是否连贯一致。
    - 信息深度：AI 生成的内容可能在深度上不如人类专家或学者创作的内容。可以对比专业领域的深度信息和细节，判断内容是否具有足够深度和专业性。
    - 文本多样性：AI 生成的内容可能在用词和句式上重复性较高，缺乏多样性。可以通过分析文本的用词和句式结构，检查是否有重复模式。
    - 一致性检查：可以通过检查文档的元数据，如创建时间和作者信息等，判断内容是否与人类创作的文档一致。
10. stu_characteristics: 学生答案主旨词。提取学生答案中的主旨词，不超过5个，用顿号【、】区隔。
11. stu_view_clarify: 学生观点凝练。不超过100字，用顿号【、】区隔。
12. stu_answer_optimization: 学生答案优化建议。不超过100字，用顿号【、】区隔。

##【字段定义】：
请严格按照如下格式仅输出JSON，不要输出python代码，不要返回多余信息，JSON中有多个字段用顿号【、】区隔：
### JSON字段：
{{
    "ai_score": 90,
    "ai_score_reason": "【任务要求】2. ai_score_reason",
    "ai_score_tags": [
        "【任务要求】3. ai_score_tags，例如: 完美试卷",
    ],
    "ai_answer": "【任务要求】4. ai_answer",
    "hit_view_list": [
        "【任务要求】5. hit_view_list[0]",
        "【任务要求】5. hit_view_list[1]",
    ],
    "stu_answer_score_key_points_match_list": [
        "30%",
        "50%",
    ],
    "hit_view_count": 5,
    "stu_answer_ai_suspicious": "10%",
    "stu_answer_ai_suspicious_reason":"【任务要求】9. stu_answer_ai_suspicious_reason",
    "stu_characteristics":"【任务要求】10. stu_characteristics",
    "stu_view_clarify":"【任务要求】11. stu_view_clarify",
    "stu_answer_optimization":"【任务要求】12. stu_answer_optimization",
}}

## 注意事项：
1. 基于给出的内容，专业和严谨的回答问题。不允许在答案中添加任何编造成分。
"""

    user_prompt_give_dimension=""""""
    
    test.questions[id].ai_prompt=system_prompt_give_dimension
    return jsonify({"prompt":system_prompt_give_dimension}), 200

def create_student_answer(id: int, student_answer: str, stu_id: int, stu_name: str) -> StudentAnswer:
    question:Question
    question=test.questions[id]
    # 创建StudentAnswer类的对象
    student_answer = StudentAnswer(stu_answer = student_answer, stu_id=stu_id, stu_name=stu_name)
    question.stu_answer_list.append(student_answer)
    return student_answer

@app.route('/update_question_student_answer', methods=['POST'])
def update_question_student_answer_route():
    id = request.form['id']
    id=int(id)
    student_answer = request.form['student_answer']
    stu_id = request.form['stu_id']
    stu_id=int(stu_id)
    stu_name = request.form['stu_name']
    student_answer_instance=create_student_answer(id, student_answer, stu_id, stu_name)
    return jsonify({"success": True, "message": "student_answer added successfully."}), 200

def generate_random_number():
    """
    根据给定的最小时间戳生成一个不超过10位的随机数。
    """
    # 确保最小时间戳是整数
    min_timestamp = int(time())

    # 生成一个基于时间戳的随机种子
    random.seed(min_timestamp)

    # 生成一个不超过10位的随机数
    return random.randint(1, 10**10 - 1)

def generate_full_random_name():
    """
    根据当前时间戳生成随机的完整中文名字或英文名字。
    """
    current_timestamp = int(time())
    random.seed(current_timestamp)

    # 中文字符集
    chinese_chars = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刘宋李张赵钱孙李周吴郑王"
    chinese_last_names = list(chinese_chars)
    chinese_first_names = "伟刚勇毅俊峰强军平保东文辉力明永健世广志义兴良海山仁波宁贵福生龙元全国胜学祥才发武新利清飞彬富顺信子杰涛昌成康星光天达安岩中茂进林有坚和彪博诚先敬震振壮会思群豪心邦承乐绍功松善厚庆磊民友裕河哲江超浩亮政谦亨奇固之轮翰朗伯宏言若鸣朋斌梁栋维启克伦翔旭鹏泽晨辰士以建家致树炎德行时泰盛雄琛钧冠策腾楠榕风航弘"
    # 英文名字
    english_first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    english_last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

    # 随机选择生成中文名或英文名
    if random.choice([True, False]):
        # 生成中文名字
        chinese_last_name = random.choice(chinese_last_names)
        chinese_first_name = ''.join(random.sample(chinese_first_names, 2))
        return chinese_last_name + chinese_first_name
    else:
        # 生成英文名字
        english_first_name = random.choice(english_first_names)
        english_last_name = random.choice(english_last_names)
        return english_first_name + " " + english_last_name

@app.route('/set_ai_autogenerate_answer', methods=['POST'])
def set_AI_autogenerate_answer_route() -> StudentAnswer:
    id = request.form['id']
    id=int(id)
    ai_mock_stu_num=request.form['ai_mock_stu_num']
    ai_mock_stu_num=int(ai_mock_stu_num)
    questions=test.questions[id];
    system_prompt_give_dimension=f"""
## 角色：你是一个AI，现在需要你回答题目，答案需要按照以下【任务要求】执行。

## 【任务要求】：
1. 答案格式像是AI回复的。
2. 答案不带个性化。
3. 答案用词和句式上重复性较高，缺乏多样性。
4. 答案输出不超过500字。
"""
    # 使用ai_mock_stu_num迭代
    for i in range(ai_mock_stu_num):    
        ai_mock_answer=GLM4_FUNCTION(system_prompt_give_dimension, questions.question_content)
        # ai_mock_stu_id=GLM4_FUNCTION("当我说开始的时候，帮我生成一个随机数，长度不超过10位", "开始")
        ai_mock_stu_id=generate_random_number()
        # ai_mock_stu_name=GLM4_FUNCTION("当我说开始的时候，帮我生成一个中文名，名字不超过3个字，寓意要好", "开始")
        ai_mock_stu_name=generate_full_random_name()
        create_student_answer(id, ai_mock_answer, ai_mock_stu_id, ai_mock_stu_name)
    return jsonify({"success": True, "message": "set_AI_autogenerate_route added successfully."}), 200

def start_ai_grading_route_second_round(id:int):
    question:Question
    question=test.questions[id]

    system_prompt = f"""
## 角色:
你是一个能够识别一段话或者一句话是否为AI生成的助手。

## 注意
- 请仔细分析【输入文本】考虑其写作风格、内容的原创性、情感表达的深度、个人经验或观点的独特性等方面。基于这些维度，判断这些文本是否可能是由AI生成的。特别注意任何看似超出通常AI生成内容能力范畴的元素，如复杂的情感表达、详细的个人经验描述等
- 请考虑AI和人类写作之间可能的细微差别。如果你在判断时感到不确定，请明确指出这种不确定性，并解释是哪些方面让你难以做出明确判断。

## question:
{question.question_content}

## workflows1:
- 回答 【question】 。使用这个回答对比【输入文本】，根据文本特征分析【输入文本】是否为AI生成。
- 输出: 
- AIGC_Percentage_CompareBotResponseReference: 取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。 
- AIGC_Percentage_CompareBotResponseReference_Reason:【输入文本】是否为AI生成的原因。

## workflows2:
1. 为 score_rules 中的每一项，使用【输入文本】计算一个疑似AI生成值，称为 Percentage，取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。
2. 根据语义将【输入文本】拆分最小的成句子或段落。每个句子或段落为一个部分称为 PartialText。
3. 接下来 PartialText 作为分析的最小粒度。
4. 对 score_rules 中的每一项，分别输入所有的 PartialText ，计算每个 PartialText 的AIGC值，称为 AIGC_Value，取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。
5. 下面是 score_rules 的每一项输出: 
- Weight: 表示该评分规则在总评分中的权重。权重越高表明该评分规则对于鉴别AI文本的重要性越大。
- High_WordCounter:  AIGC_Value 高的 PartialText 的字数之和。
- Middle_WordCounter: AIGC_Value 中等的 PartialText 的字数之和。 
- Low_WordCounter: AIGC_Value 低的 PartialText 的字数之和。 
- Percentage: 取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。 
- Reason: 【输入文本】是否为AI生成的原因。
- High_WordCounter_Mul_Percentage: 值为 High_WordCounter * Percentage。

## score_rules:
1. AIGC_LanguageStyle: 语言风格分析
- 计算规则: 计算每个 PartialText 与人类文本的相似度。AI 生成的内容可能在语言风格上过于统一，缺乏个性和情感色彩。人类文本风格：人类文本的风格通常具有多样性，包括幽默、正式、口语化等。AI生成的内容可能过于统一，缺乏个性和情感色彩。可以根据 PartialText 的语言风格，判断是否与人类的自然表达方式一致。
2. AIGC_GrammarStructure: 语法结构分析
- 计算规则: 计算每个 PartialText 的语法错误率。AI 生成的内容可能在语法结构上存在错误或过于规范。可以通过语法分析工具，检查 PartialText 的语法结构是否正确。
3. AIGC_FactAccuracy: 事实准确性分析
- 计算规则: 计算每个PartialText的事实准确性。AI 生成的内容可能在事实准确性上存在偏差。可以通过事实核查工具，检查 PartialText 中的事实是否准确。
4. AIGC_LogicalConsistency: 逻辑一致性分析
- 计算规则: 计算PartialText之间的逻辑连贯性。AI 生成的内容可能在逻辑上存在跳跃或不连贯。可以通过逻辑分析工具，检查 PartialText 的逻辑是否连贯。
5. AIGC_InformationDepth: 信息深度分析
- 计算规则: 计算每个PartialText的信息深度。AI 生成的内容可能在深度上不如人类专家或学者创作的内容。可以对比专业领域的深度信息和细节，判断内容是否具有足够深度和专业性。
6. AIGC_TextDiversity: 文本多样性分析
- 计算规则: 计算每个PartialText的用词和句式多样性。AI 生成的内容可能在用词和句式上重复性较高，缺乏多样性。可以通过分析 PartialText 的用词和句式结构，检查是否有重复模式。
7. AIGC_TextCoherence: 文本连贯性分析
- 计算规则: 计算每个PartialText的段落和句子连贯性。AI 生成的内容可能在段落和句子之间缺乏连贯性。可以通过分析 PartialText 的段落和句子结构，检查是否有连贯性。
8. AIGC_HumanReadability: 人类可读性分析
- 计算规则: 计算每个PartialText的人类可读性。AI 生成的内容可能在人类可读性上不如人类专家或学者创作的内容。可以对比人类专家或学者创作的内容，判断内容是否具有足够的人类可读性。

## workflow3:
1. 将workflow1和workflow2连起来执行3遍。
2. 根据前面的分析结果，总结可能是AI生成的内容的可能性和原因
3. 计算规则: 根据前面执行3遍的评分结果计算均值，包括: AIGC_CompareBotResponseReference 、 AIGC_LanguageStyle 、 AIGC_GrammarStructure 、 AIGC_FactAccuracy 、 AIGC_LogicalConsistency 、 AIGC_InformationDept 、 AIGC_TextDiversity 、 AIGC_TextCoherence 、 AIGC_HumanReadability ，总结可能是AI生成的内容的原因，不超过200字。包括但不限于: 语言风格、语法结构、事实准确性、逻辑连贯性、信息深度、文本多样性、文本连贯性、人类可读性等。
4. 输出：
- ALL_WordCounter : 表示【输入文本】的总字数。 
- AIGC_Percentage_Final : 取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。 
- AIGC_Reasons_Final : 表示可能是AI生成的内容的可能性和原因。

##【输出字段定义】:
请严格按照如下格式仅输出JSON，不要输出python代码，不要返回多余信息，JSON中有多个字段用顿号【、】区隔:
### JSON字段:
{{
    "AIGC_Percentage_CompareBotResponseReference": 0.5,
    "AIGC_Percentage_CompareBotResponseReference_Reason": "【输入文本】是否为AI生成的原因",
    "AIGC_LanguageStyle": {{
        "weight": 1,
        "Percentage": 1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_GrammarStructure": {{
        "weight": 0.1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_FactAccuracy": {{
        "weight": 2,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_LogicalConsistency": {{
        "weight": 1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_InformationDepth": {{
        "weight": 1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_TextDiversity": {{
        "weight": 1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_TextCoherence": {{
        "weight": 0.1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500
    }},
    "AIGC_HumanReadability": {{
        "weight": 2,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "ALL_WordCounter": 0,
    "AIGC_Percentage_Final": 1,
    "AIGC_Reasons_Final": "总结文本是通过AI生成的原因"
}}
"""

    for stu_answer in question.stu_answer_list:
        user_prompt = f"""
## 【输入文本】：
{stu_answer.stu_answer}
"""
        ai_grading_json_str=GLM4_FUNCTION(system_prompt, user_prompt)
        json_str,json_dict=try_parse_json_object(ai_grading_json_str)        

        json_dict['AIGC_LanguageStyle']['weight']=1
        json_dict['AIGC_GrammarStructure']['weight']=1
        json_dict['AIGC_FactAccuracy']['weight']=1
        json_dict['AIGC_LogicalConsistency']['weight']=1
        json_dict['AIGC_InformationDepth']['weight']=1
        json_dict['AIGC_TextDiversity']['weight']=1
        json_dict['AIGC_TextCoherence']['weight']=1
        json_dict['AIGC_HumanReadability']['weight']=1
        ALL_WEIGHT= \
            json_dict['AIGC_LanguageStyle']['weight']+ \
            json_dict['AIGC_GrammarStructure']['weight']+\
            json_dict['AIGC_FactAccuracy']['weight']+ \
            json_dict['AIGC_LogicalConsistency']['weight']+\
            json_dict['AIGC_InformationDepth']['weight']+\
            json_dict['AIGC_TextDiversity']['weight']+\
            json_dict['AIGC_TextCoherence']['weight']+\
            json_dict['AIGC_HumanReadability']['weight']

        ALL_AL_WD= \
            json_dict['AIGC_LanguageStyle']['weight'] / ALL_WEIGHT * json_dict['AIGC_LanguageStyle']['High_WordCounter']+ \
            json_dict['AIGC_GrammarStructure']['weight'] / ALL_WEIGHT *json_dict['AIGC_GrammarStructure']['High_WordCounter']+\
            json_dict['AIGC_FactAccuracy']['weight'] / ALL_WEIGHT *json_dict['AIGC_FactAccuracy']['High_WordCounter']+ \
            json_dict['AIGC_LogicalConsistency']['weight'] / ALL_WEIGHT *json_dict['AIGC_LogicalConsistency']['High_WordCounter']+\
            json_dict['AIGC_InformationDepth']['weight'] / ALL_WEIGHT *json_dict['AIGC_InformationDepth']['High_WordCounter']+\
            json_dict['AIGC_TextDiversity']['weight'] / ALL_WEIGHT *json_dict['AIGC_TextDiversity']['High_WordCounter']+\
            json_dict['AIGC_TextCoherence']['weight'] / ALL_WEIGHT *json_dict['AIGC_TextCoherence']['High_WordCounter']+\
            json_dict['AIGC_HumanReadability']['weight'] / ALL_WEIGHT *json_dict['AIGC_HumanReadability']['High_WordCounter']
        ALL_WD=json_dict['ALL_WordCounter']
        final_P:float=ALL_AL_WD/ALL_WD
        # 对final_P进行四舍五入，保留两位小数
        final_P = round(final_P, 2)
        # print("final P=",ALL_AL_WD/ALL_WD)
        stu_answer.stu_answer_ai_suspicious=final_P
        stu_answer.stu_answer_ai_suspicious_reason=json_dict['AIGC_Reasons_Final']
        # "完美试卷"、"高分试卷"、"疑似AI"
        stu_answer.ai_score_tags=[]
        if(final_P>0.7):
            stu_answer.ai_score_tags.append("疑似AI")
            print("疑似AI-",stu_answer.stu_name)
            
        if(final_P<=0.6 and stu_answer.ai_score>=90):
            stu_answer.ai_score_tags.append("完美试卷")
            print("完美试卷-",stu_answer.stu_name)

        elif(stu_answer.ai_score>=90):
            stu_answer.ai_score_tags.append("高分试卷")
            print("高分试卷-",stu_answer.stu_name)

@app.route('/start_ai_grading', methods=['POST'])
def start_ai_grading_route() -> StudentAnswer:
    id = request.form['id']
    id=int(id)
    question:Question
    question=test.questions[id]
    print("question.question_content=",question.question_content)
    system_prompt = f"""
## 角色:
你是一个能够识别一段话或者一句话是否为AI生成的助手。

## 注意
- 请仔细分析【输入文本】考虑其写作风格、内容的原创性、情感表达的深度、个人经验或观点的独特性等方面。基于这些维度，判断这些文本是否可能是由AI生成的。特别注意任何看似超出通常AI生成内容能力范畴的元素，如复杂的情感表达、详细的个人经验描述等
- 请考虑AI和人类写作之间可能的细微差别。如果你在判断时感到不确定，请明确指出这种不确定性，并解释是哪些方面让你难以做出明确判断。

## question:
{question.question_content}

## workflows1:
- 回答 【question】 。使用这个回答对比【输入文本】，根据文本特征分析【输入文本】是否为AI生成。
- 输出: 
- AIGC_Percentage_CompareBotResponseReference: 取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。 
- AIGC_Percentage_CompareBotResponseReference_Reason:【输入文本】是否为AI生成的原因。

## workflows2:
1. 为 score_rules 中的每一项，使用【输入文本】计算一个疑似AI生成值，称为 Percentage，取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。
2. 根据语义将【输入文本】拆分最小的成句子或段落。每个句子或段落为一个部分称为 PartialText。
3. 接下来 PartialText 作为分析的最小粒度。
4. 对 score_rules 中的每一项，分别输入所有的 PartialText ，计算每个 PartialText 的AIGC值，称为 AIGC_Value，取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。
5. 下面是 score_rules 的每一项输出: 
- Weight: 表示该评分规则在总评分中的权重。权重越高表明该评分规则对于鉴别AI文本的重要性越大。
- High_WordCounter:  AIGC_Value 高的 PartialText 的字数之和。
- Middle_WordCounter: AIGC_Value 中等的 PartialText 的字数之和。 
- Low_WordCounter: AIGC_Value 低的 PartialText 的字数之和。 
- Percentage: 取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。 
- Reason: 【输入文本】是否为AI生成的原因。
- High_WordCounter_Mul_Percentage: 值为 High_WordCounter * Percentage。

## score_rules:
1. AIGC_LanguageStyle: 语言风格分析
- 计算规则: 计算每个 PartialText 与人类文本的相似度。AI 生成的内容可能在语言风格上过于统一，缺乏个性和情感色彩。人类文本风格：人类文本的风格通常具有多样性，包括幽默、正式、口语化等。AI生成的内容可能过于统一，缺乏个性和情感色彩。可以根据 PartialText 的语言风格，判断是否与人类的自然表达方式一致。
2. AIGC_GrammarStructure: 语法结构分析
- 计算规则: 计算每个 PartialText 的语法错误率。AI 生成的内容可能在语法结构上存在错误或过于规范。可以通过语法分析工具，检查 PartialText 的语法结构是否正确。
3. AIGC_FactAccuracy: 事实准确性分析
- 计算规则: 计算每个PartialText的事实准确性。AI 生成的内容可能在事实准确性上存在偏差。可以通过事实核查工具，检查 PartialText 中的事实是否准确。
4. AIGC_LogicalConsistency: 逻辑一致性分析
- 计算规则: 计算PartialText之间的逻辑连贯性。AI 生成的内容可能在逻辑上存在跳跃或不连贯。可以通过逻辑分析工具，检查 PartialText 的逻辑是否连贯。
5. AIGC_InformationDepth: 信息深度分析
- 计算规则: 计算每个PartialText的信息深度。AI 生成的内容可能在深度上不如人类专家或学者创作的内容。可以对比专业领域的深度信息和细节，判断内容是否具有足够深度和专业性。
6. AIGC_TextDiversity: 文本多样性分析
- 计算规则: 计算每个PartialText的用词和句式多样性。AI 生成的内容可能在用词和句式上重复性较高，缺乏多样性。可以通过分析 PartialText 的用词和句式结构，检查是否有重复模式。
7. AIGC_TextCoherence: 文本连贯性分析
- 计算规则: 计算每个PartialText的段落和句子连贯性。AI 生成的内容可能在段落和句子之间缺乏连贯性。可以通过分析 PartialText 的段落和句子结构，检查是否有连贯性。
8. AIGC_HumanReadability: 人类可读性分析
- 计算规则: 计算每个PartialText的人类可读性。AI 生成的内容可能在人类可读性上不如人类专家或学者创作的内容。可以对比人类专家或学者创作的内容，判断内容是否具有足够的人类可读性。

## workflow3:
1. 将workflow1和workflow2连起来执行3遍。
2. 根据前面的分析结果，总结可能是AI生成的内容的可能性和原因
3. 计算规则: 根据前面执行3遍的评分结果计算均值，包括: AIGC_CompareBotResponseReference 、 AIGC_LanguageStyle 、 AIGC_GrammarStructure 、 AIGC_FactAccuracy 、 AIGC_LogicalConsistency 、 AIGC_InformationDept 、 AIGC_TextDiversity 、 AIGC_TextCoherence 、 AIGC_HumanReadability ，总结可能是AI生成的内容的原因，不超过200字。包括但不限于: 语言风格、语法结构、事实准确性、逻辑连贯性、信息深度、文本多样性、文本连贯性、人类可读性等。
4. 输出：
- ALL_WordCounter : 表示【输入文本】的总字数。 
- AIGC_Percentage_Final : 取值范围为0-1，0表示确定不是AI生成，1表示确定是AI生成。 
- AIGC_Reasons_Final : 表示可能是AI生成的内容的可能性和原因。

##【输出字段定义】:
请严格按照如下格式仅输出JSON，不要输出python代码，不要返回多余信息，JSON中有多个字段用顿号【、】区隔:
### JSON字段:
{{
    "AIGC_Percentage_CompareBotResponseReference": 0.5,
    "AIGC_Percentage_CompareBotResponseReference_Reason": "【输入文本】是否为AI生成的原因",
    "AIGC_LanguageStyle": {{
        "weight": 1,
        "Percentage": 1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_GrammarStructure": {{
        "weight": 0.1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_FactAccuracy": {{
        "weight": 2,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_LogicalConsistency": {{
        "weight": 1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_InformationDepth": {{
        "weight": 1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_TextDiversity": {{
        "weight": 1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "AIGC_TextCoherence": {{
        "weight": 0.1,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500
    }},
    "AIGC_HumanReadability": {{
        "weight": 2,
        "Percentage":1,
        "Reason": "【输入文本】是否为AI生成的原因",
        "High_WordCounter": 500,
        "Middle_WordCounter": 300,
        "Low_WordCounter": 100,
        "High_WordCounter_Mul_Percentage": 500,
    }},
    "ALL_WordCounter": 0,
    "AIGC_Percentage_Final": 1,
    "AIGC_Reasons_Final": "总结文本是通过AI生成的原因"
}}
"""

    # 使用ai_mock_stu_num迭代
    for stu_answer in question.stu_answer_list:
        # print(f"AI Grading Response for Student ID {stu_answer.stu_id}")
        # print("question.ai_prompt=", question.ai_prompt)
        # print("stu_answer.stu_answer", stu_answer.stu_answer)
        ai_grading_json_str=GLM4_FUNCTION(question.ai_prompt, stu_answer.stu_answer)
        # print("ai_grading_json_str=", ai_grading_json_str)
        json_str,ai_grading_json=try_parse_json_object(ai_grading_json_str)        
        # print("ai_grading_json=", ai_grading_json)

        ai_score=ai_grading_json['ai_score']
        ai_score_reason=ai_grading_json['ai_score_reason']
        ai_score_tags=ai_grading_json['ai_score_tags']
        ai_answer=ai_grading_json['ai_answer']
        hit_view_list=ai_grading_json['hit_view_list']
        stu_answer_score_key_points_match_list=ai_grading_json['stu_answer_score_key_points_match_list']
        hit_view_count=ai_grading_json['hit_view_count']
        stu_answer_ai_suspicious=ai_grading_json['stu_answer_ai_suspicious']
        stu_answer_ai_suspicious_reason=ai_grading_json['stu_answer_ai_suspicious_reason']
        stu_characteristics=ai_grading_json['stu_characteristics']
        stu_view_clarify=ai_grading_json['stu_view_clarify']
        
        stu_answer.ai_score=float(ai_score)
        stu_answer.ai_score_reason=ai_score_reason
        # stu_answer.ai_score_tags=ai_score_tags
        question.ai_answer=ai_answer
        stu_answer.hit_view_count=hit_view_count
        stu_answer.hit_view_list=hit_view_list
        stu_answer.stu_answer_score_key_points_match_list=[extract_first_real_number(x) for x in stu_answer_score_key_points_match_list]
        # stu_answer.stu_answer_ai_suspicious=extract_first_real_number(stu_answer_ai_suspicious)
        # stu_answer.stu_answer_ai_suspicious_reason=stu_answer_ai_suspicious_reason
        stu_answer.stu_characteristics=stu_characteristics
        stu_answer.stu_view_clarify=stu_view_clarify
        stu_answer.ai_status=True
        stu_answer.stu_answer_optimization=ai_grading_json['stu_answer_optimization']
        
        # 根据 ai_score 更新 stu_score_level ，其中 大于等于90分为A，80-89分为B，70-79分为C，60-69分为D，60分以下为E
        if stu_answer.ai_score >= 90:
            stu_answer.stu_score_level = 'A'
        elif stu_answer.ai_score >= 80:
            stu_answer.stu_score_level = 'B'
        elif stu_answer.ai_score >= 70:
            stu_answer.stu_score_level = 'C'
        elif stu_answer.ai_score >= 60:
            stu_answer.stu_score_level = 'D'
        else:
            stu_answer.stu_score_level = 'E'

        user_prompt = f"""
## 【输入文本】：
{stu_answer.stu_answer}
"""
        ai_grading_json_str=GLM4_FUNCTION(system_prompt, user_prompt)
        json_str,json_dict=try_parse_json_object(ai_grading_json_str)        

        json_dict['AIGC_LanguageStyle']['weight']=1
        json_dict['AIGC_GrammarStructure']['weight']=1
        json_dict['AIGC_FactAccuracy']['weight']=1
        json_dict['AIGC_LogicalConsistency']['weight']=1
        json_dict['AIGC_InformationDepth']['weight']=1
        json_dict['AIGC_TextDiversity']['weight']=1
        json_dict['AIGC_TextCoherence']['weight']=1
        json_dict['AIGC_HumanReadability']['weight']=1

        ALL_WEIGHT= \
            json_dict['AIGC_LanguageStyle']['weight']+ \
            json_dict['AIGC_GrammarStructure']['weight']+\
            json_dict['AIGC_FactAccuracy']['weight']+ \
            json_dict['AIGC_LogicalConsistency']['weight']+\
            json_dict['AIGC_InformationDepth']['weight']+\
            json_dict['AIGC_TextDiversity']['weight']+\
            json_dict['AIGC_TextCoherence']['weight']+\
            json_dict['AIGC_HumanReadability']['weight']

        ALL_AL_WD= \
            json_dict['AIGC_LanguageStyle']['weight'] / ALL_WEIGHT * json_dict['AIGC_LanguageStyle']['High_WordCounter']+ \
            json_dict['AIGC_GrammarStructure']['weight'] / ALL_WEIGHT *json_dict['AIGC_GrammarStructure']['High_WordCounter']+\
            json_dict['AIGC_FactAccuracy']['weight'] / ALL_WEIGHT *json_dict['AIGC_FactAccuracy']['High_WordCounter']+ \
            json_dict['AIGC_LogicalConsistency']['weight'] / ALL_WEIGHT *json_dict['AIGC_LogicalConsistency']['High_WordCounter']+\
            json_dict['AIGC_InformationDepth']['weight'] / ALL_WEIGHT *json_dict['AIGC_InformationDepth']['High_WordCounter']+\
            json_dict['AIGC_TextDiversity']['weight'] / ALL_WEIGHT *json_dict['AIGC_TextDiversity']['High_WordCounter']+\
            json_dict['AIGC_TextCoherence']['weight'] / ALL_WEIGHT *json_dict['AIGC_TextCoherence']['High_WordCounter']+\
            json_dict['AIGC_HumanReadability']['weight'] / ALL_WEIGHT *json_dict['AIGC_HumanReadability']['High_WordCounter']
        
        ALL_WD=json_dict['ALL_WordCounter']
        final_P:float=ALL_AL_WD/ALL_WD
        # 对final_P进行四舍五入，保留两位小数
        final_P = round(final_P, 2)
        # print("final P=",ALL_AL_WD/ALL_WD)
        stu_answer.stu_answer_ai_suspicious=final_P
        stu_answer.stu_answer_ai_suspicious_reason=json_dict['AIGC_Reasons_Final']
        # "完美试卷"、"高分试卷"、"疑似AI"
        stu_answer.ai_score_tags=[]
        if(final_P>0.7):
            stu_answer.ai_score_tags.append("疑似AI")
            print("疑似AI-",stu_answer.stu_name)
        if(final_P<=0.6 and stu_answer.ai_score>=90):
            stu_answer.ai_score_tags.append("完美试卷")
            print("完美试卷-",stu_answer.stu_name)
        elif(stu_answer.ai_score>=90):
            stu_answer.ai_score_tags.append("高分试卷")
            print("高分试卷-",stu_answer.stu_name)
    return jsonify({"success": True, "message": "start_ai_grading successfully."}), 200

@app.route('/get_one_stu_answer_detail', methods=['GET'])
def get_one_stu_answer_detail_route():
    id = request.args.get('id')
    id = int(id)
    stu_id = request.args.get('stu_id')
    stu_id = int(stu_id)
    stu_answer_dict= {}
    # 使用dataclass_to_dict函数转换Question实例为字典
    question=test.questions[id]
    for stu_answer in question.stu_answer_list:
        if stu_answer.stu_id==stu_id:
                stu_answer_dict= dataclass_to_dict(stu_answer)
    return jsonify(stu_answer_dict), 200


@app.route('/make_sure_ai_grade', methods=['POST'])
def make_sure_ai_grade_route() -> StudentAnswer:
    id = request.form['id']
    id=int(id)
    stu_id = request.form['stu_id']
    stu_id=int(stu_id)
    teacher_score=request.form['teacher_score']
    teacher_score=float(teacher_score)
    teacher_score_reason=request.form['teacher_score_reason']
    stu_score_level=request.form['stu_score_level']
    
    question:Question
    question=test.questions[id];
    
    # 使用ai_mock_stu_num迭代
    for stu_answer in question.stu_answer_list:
        if stu_answer.stu_id==stu_id:
            stu_answer.teacher_score=teacher_score
            stu_answer.teacher_score_reason=teacher_score_reason
            stu_answer.stu_score_level=stu_score_level

    return jsonify({"success": True, "message": "make_sure_ai_grade_route successfully."}), 200

@app.route('/auto_make_sure_all_ai_grade', methods=['POST'])
def auto_make_sure_all_ai_grade_route() -> StudentAnswer:
    id = request.form['id']
    id=int(id)

    question:Question
    question=test.questions[id];

    # 使用ai_mock_stu_num迭代
    for stu_answer in question.stu_answer_list:
        if(stu_answer.teacher_score==0):
            stu_answer.teacher_score=stu_answer.ai_score

    return jsonify({"success": True, "message": "auto_make_sure_all_ai_grade successfully."}), 200


def determine_difficulty(a_count:float, b_count:float, c_count:float, d_count:float, e_count:float):
    total_students = a_count + b_count + c_count + d_count + e_count

    if total_students == 0:
        return ''

    high_grades_ratio = (a_count) / total_students
    low_grades_ratio = (d_count + e_count) / total_students

    if high_grades_ratio > 0.7:
        return '容易'
    elif low_grades_ratio > 0.7:
        return '难'
    else:
        return '适中'

def extract_first_real_number(s):
    # 定义一个正则表达式来匹配实数
    # 实数的匹配模式包括可选的正负号、整数部分、可选的小数部分以及可选的科学记数法表示
    pattern = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'
    
    # 使用re.search查找第一个匹配的实数
    match = re.search(pattern, s)
    # 如果找到了匹配的实数，将其转换为float类型并返回
    if match:
        num = float(match.group())
        if 0 <= num <= 1:
            return num * 100
        elif num > 100:
            return 100
        elif num < 0:
            return 0
        else:
            return num
    else:
        # 如果没有找到匹配的实数，可以返回None或者抛出一个异常
        return 0

@app.route('/create_chart', methods=['POST'])
def create_chart_route() -> StudentAnswer:
    id = request.form['id']
    id=int(id)
    question:Question
    question=test.questions[id];
    # question.score_level_count
    question.score_level_labels=["A","B","C","D","E"]
    question.score_level_count=[0,0,0,0,0]

    # 根据得分要点数先初始化答题要点矩阵图
    
    # 获取question.score_key_points的元素个数
    number_of_key_points = len(question.score_key_points)
    question.score_key_points_rank = [[] for _ in range(number_of_key_points)]
    
    question.ai_tag_list = ["完美试卷","高分试卷","疑似AI"]
    question.ai_tag_count = [0, 0, 0]
    
    question.score_key_hit_points_count=[ 0 for _ in range(number_of_key_points)]
    question.score_key_miss_points_count=[ 0 for _ in range(number_of_key_points)]
    # 生成列表，元素分别丛1到len(number_of_key_points)
    question.score_key_points_num = list(range(1, number_of_key_points + 1))
    # 主旨词拼接
    main_words=""
    for stu_answer in question.stu_answer_list:
        if stu_answer.ai_status:
            # chart 1 根据stu_answer.stu_score_level更新question.score_level_count
            if(stu_answer.stu_score_level=="A"):
                question.score_level_count[0]+=1
            elif(stu_answer.stu_score_level=="B"):
                question.score_level_count[1]+=1
            elif(stu_answer.stu_score_level=="C"):
                question.score_level_count[2]+=1
            elif(stu_answer.stu_score_level=="D"):
                question.score_level_count[3]+=1
            elif(stu_answer.stu_score_level=="E"):
                question.score_level_count[4]+=1
            

            # chart3 ai标签人数,{"完美试卷": 1,"高分试卷": 1,"疑似AI":1,"雷同试卷":1,"疑似抄袭":1},
            # "完美试卷"、"高分试卷"、"疑似AI" AI标签的数量统计
            for ai_tag in stu_answer.ai_score_tags:
                if "完美" in ai_tag:
                    question.ai_tag_count[0] += 1
                if "高分" in ai_tag:
                    question.ai_tag_count[1] += 1
                if "AI" in ai_tag:
                    question.ai_tag_count[2] += 1
                    
            # chart4 每个得分要点的得分人数统计

            ishit:bool
            value:float
            # 答题要点矩阵图s
            for indexQue, standKeyPoint in enumerate(question.score_key_points):
                ishit=0
                for indexStu,stuKeyPoint in enumerate(stu_answer.hit_view_list):
                    if(stuKeyPoint == standKeyPoint):
                        value=0.0
                        if(indexStu<len(stu_answer.stu_answer_score_key_points_match_list)):
                            value=(stu_answer.stu_answer_score_key_points_match_list[indexStu])
                        question.score_key_points_rank[indexQue].append(ScoreKeyPoint(stu_answer.stu_name, stu_answer.stu_id, standKeyPoint, value))
                        ishit=1
                        question.score_key_hit_points_count[indexQue]=question.score_key_hit_points_count[indexQue]+1
                        break;
                if not ishit:
                    question.score_key_points_rank[indexQue].append(ScoreKeyPoint(stu_answer.stu_name, stu_answer.stu_id, standKeyPoint, 0.0))
                    question.score_key_miss_points_count[indexQue]=question.score_key_miss_points_count[indexQue]+1
        #把stu_answer.stu_characteristics使用分隔符拼接起来，并拼接给main_words字符串
        main_words = main_words + " "+stu_answer.stu_characteristics + " "



    # chart2 分别给出题目偏难和偏容易的情况
    # 如果A、B、C、D、E的数量都相差不超过5则认为题目难度适中，否则认为题目较偏难或较易
    question.question_difficulty=determine_difficulty(question.score_level_count[0],question.score_level_count[1],question.score_level_count[2],question.score_level_count[3],question.score_level_count[4])
    

    # chart5 score rank
    # 根据question.stu_answer_list中的teacher_score大小，给每个stu_answer的teacher_score_rank排序值
    question.stu_answer_list.sort(key=lambda x: x.teacher_score, reverse=True)
    # 根据question.stu_answer_list中的teacher_score_rank排序值，给每个stu_answer的teacher_score_rank赋值
    for indexStu, stu_answer in enumerate(question.stu_answer_list):
        question.stu_answer_list[indexStu].teacher_score_rank = indexStu + 1
    
    # chart 6 主旨词分布
    system_prompt_give_dimension=f"""
##【任务要求】：
根据我提供的【主旨词列表】给出每个主旨词出现次数。【主旨词列表】中每个主旨词用分隔符或特殊字符分隔。
1. main_idea_list ：主旨词列表，每个主旨词出现的次数在对应index的main_idea_list_count列表中
2. main_idea_list_count ：主旨词出现次数列表

##【字段定义】：
请严格按照如下格式仅输出JSON，不要输出python代码，不要返回多余信息，JSON中有多个字段用顿号【、】区隔：
### JSON字段：
{{
"main_idea_list":[
    "idea1",
    "idea2",
    ...
],
"main_idea_list_count":[
    1,
    2,
    ...
]
}}

## 注意事项：
1. 基于给出的内容，专业和严谨的回答问题。不允许添加任何编造成分。
"""
    user_prompt_give_dimension=f"""
【主旨词列表】：
{main_words}
"""
    json_str=GLM4_FUNCTION(system_prompt_give_dimension, user_prompt_give_dimension)
    # 解析JSON字符串
    json_str,json_dict=try_parse_json_object(json_str)
    # 主旨词列表
    # 根据main_word_list和main_word_distribution_count两个列表长度最小的那个，剪裁这两个列表，使它们俩长度相等
    if len(json_dict["main_idea_list"]) > len(json_dict["main_idea_list_count"]):
        json_dict["main_idea_list"] = json_dict["main_idea_list"][:len(json_dict["main_idea_list_count"])]
    else:
        json_dict["main_idea_list_count"] = json_dict["main_idea_list_count"][:len(json_dict["main_idea_list"])]

    question.main_word_list=json_dict["main_idea_list"]
    # 主旨词分布统计
    question.main_word_distribution_count=json_dict["main_idea_list_count"]

    return jsonify({"success": True, "message": "start_ai_grading successfully."}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7999)
