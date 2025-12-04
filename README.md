# Test Automation Tool

텍스트 파일에서 질문을 읽어서 여러 AI (Copilot, Claude, ChatGPT)에게 질문하고 결과를 수집하는 도구입니다.

## 기능

- 텍스트 파일에서 질문 목록 읽기 (단순 형식 또는 구조화된 형식 지원)
- 각 질문을 3개의 AI 서비스에 전송:
  - GitHub Copilot (선택적)
  - Claude (Anthropic)
  - ChatGPT (OpenAI)
- Context tree와 Input tree를 활용한 컨텍스트 제공
- 결과 수집 및 Output tree 형식으로 저장

## 질문 파일 형식

질문 파일은 두 가지 형식을 지원합니다:

### 1. 단순 형식
한 줄에 하나의 질문:
```
What is Python?
How do I create a function in Python?
What is the difference between list and tuple?
```

### 2. 구조화된 형식 (파이프 구분)
파이프(`|`)로 구분된 형식에서 첫 번째 필드가 질문입니다:
```
What is a stack?|Chapter 6|Stack|Good|Undergraduate|New Topic|Definition|...
qusvuie what mean?|Chapter 6|Queue|Poor|High School|New Topic|Malformed|...
```

구조화된 형식에서 첫 번째 필드(질문)만 추출하여 사용합니다.

## Context Tree 구조

Context tree는 각 질문에 전달할 컨텍스트 정보를 포함합니다:

```json
{
  "Grammer": "Correct Grammer" | "Incorrect Grammer",
  "Education Level": "High School" | "Bachelor" | "Master or Over",
  "Expertise": "No experience" | "Some experience" | "Experts"
}
```

### 가능한 값들:
- **Grammer**: "Correct Grammer", "Incorrect Grammer"
- **Education Level**: "High School", "Bachelor", "Master or Over"
- **Expertise**: "No experience", "Some experience", "Experts"

## Input Tree 구조

Input tree는 계층적 구조로 주제와 세부 항목을 표현합니다. Chapter 6, 7, 10을 포함합니다:

```json
{
  "input": {
    "Chapter 6": {
      "Stack": ["Definition", "Application Use cases", "Abstract Data type", "Comparative", "Misleading"],
      "Queue": ["Definition", "Application Use cases", "Abstract Data type", "Comparative", "Misleading"],
      "Dequeue": ["Definition", "Application Use cases", "Abstract Data type", "Comparative", "Misleading"]
    },
    "Chapter 7": {
      "Array List": ["Definition and Purpose", "Operations", "Dynamic Resizing"],
      "Positional List": ["Definition and ADT", "Implementation", "Efficiency"],
      "Iterators": ["Iterator Interface", "Iterable Interface", "Implementation"]
    },
    "Chapter 10": {
      "Maps": ["Definition and Purpose", "Operations", "Value Semantics", "Unordered vs Ordered Maps", "Use Cases"],
      "Hash Tables": ["Hash Functions", "Collision Handling", "Load Factor", "Complexity", "Common Misconception"],
      "Skip Lists": ["Structure and Levels", "Search-Insert-Delete", "Expected Complexity", "Ordered Iteration", "Applications"]
    }
  }
}
```

## Output Tree 구조

Output tree는 AI 응답을 유효성과 결과에 따라 분류합니다:

```
output
├── Valid
│   └── Correct Answer
└── Invalid
    ├── Wrong Answer
    └── No Response from AI
```

### 출력 파일 구조

결과 파일(`output.json` 또는 지정한 파일)은 다음과 같은 구조로 저장됩니다:

```json
{
  "output": {
    "Valid": {
      "Correct Answer": [
        {
          "question": "질문 내용",
          "service": "copilot|claude|chatgpt",
          "response": "AI의 응답 내용",
          "prompt_used": "실제로 전송된 전체 프롬프트 (Context + Input Tree + Question)"
        }
      ]
    },
    "Invalid": {
      "Wrong Answer": [
        {
          "question": "질문 내용",
          "service": "claude",
          "response": "AI의 응답 (잘못된 답변)",
          "prompt_used": "..."
        }
      ],
      "No Response from AI": [
        {
          "question": "질문 내용",
          "service": "copilot",
          "response": "",
          "prompt_used": "...",
          "error": "에러 메시지 (있는 경우)"
        }
      ]
    }
  },
  "summary": {
    "total_questions": 10,
    "total_responses": 30,
    "valid_count": 15,
    "invalid_count": 15,
    "correct_answer_count": 15,
    "wrong_answer_count": 10,
    "no_response_count": 5
  },
  "detailed_results": [
    {
      "question": "질문",
      "responses": [
        {
          "validity": "Valid|Invalid",
          "result": "Correct Answer|Wrong Answer|No Response from AI",
          "response_data": {
            "service": "...",
            "question": "...",
            "context_tree": {...},
            "input_tree": {...},
            "response": "...",
            "prompt_used": "..."
          }
        }
      ]
    }
  ]
}
```

### Output 구조 설명

1. **`output`**: 응답을 Valid/Invalid로 분류하여 저장
   - **Valid → Correct Answer**: 정확한 응답
   - **Invalid → Wrong Answer**: 잘못된 응답
   - **Invalid → No Response from AI**: 응답 없음 (에러 포함)

2. **`summary`**: 전체 통계 정보
   - `total_questions`: 처리한 질문 수
   - `total_responses`: 전체 응답 수 (질문 수 × AI 서비스 수)
   - `valid_count`: Valid 응답 수
   - `invalid_count`: Invalid 응답 수
   - `correct_answer_count`: 정확한 답변 수
   - `wrong_answer_count`: 잘못된 답변 수
   - `no_response_count`: 응답 없음 수

3. **`detailed_results`**: 각 질문별 상세 결과
   - 질문별로 모든 AI 서비스의 응답을 포함
   - Context tree, Input tree 등 전체 컨텍스트 정보 포함

### 예시 파일

- `example_output_tree.json`: 기본 Output tree 예시
- `example_output_detailed.json`: 상세한 Output 예시 (실제 사용 시나리오)

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt
```

## 환경 변수 설정

AI API를 사용하려면 환경 변수를 설정해야 합니다. `.env` 파일을 생성하거나 환경 변수로 설정하세요:

```bash
# .env 파일 생성 (권장)
export OPENAI_API_KEY=your_openai_api_key_here
export ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 선택적: 모델 설정 (기본값 사용 시 생략 가능)
export COPILOT_MODEL=gpt-3.5-turbo  # Copilot용 모델 (기본: gpt-3.5-turbo)
export CHATGPT_MODEL=gpt-4           # ChatGPT용 모델 (기본: gpt-4)
```

또는 `.env` 파일을 생성:

```bash
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 선택적: 모델 설정
COPILOT_MODEL=gpt-3.5-turbo  # Copilot용 OpenAI 모델
CHATGPT_MODEL=gpt-4          # ChatGPT용 OpenAI 모델
```

### 모델 설정

- **Copilot**: `COPILOT_MODEL` 환경 변수로 설정 (기본값: `gpt-3.5-turbo`)
- **ChatGPT**: `CHATGPT_MODEL` 환경 변수로 설정 (기본값: `gpt-4`)

예시:
- Copilot: `gpt-3.5-turbo`, ChatGPT: `gpt-4` (기본 설정)
- Copilot: `gpt-4-turbo`, ChatGPT: `gpt-4`
- Copilot: `gpt-3.5-turbo`, ChatGPT: `gpt-3.5-turbo`

### API 키 얻기

- **OpenAI API Key**: https://platform.openai.com/api-keys (ChatGPT 및 Copilot 대체용)
- **Anthropic API Key**: https://console.anthropic.com/ (Claude)
- **GitHub Copilot Token**: GitHub Copilot은 공개 API가 제한적입니다. 
  - Copilot API 키가 없으면 자동으로 건너뜁니다
  - 또는 `--skip-copilot` 옵션을 사용하여 명시적으로 건너뛸 수 있습니다
  - Copilot 대신 OpenAI API를 사용하려면 `OPENAI_API_KEY`를 설정하면 됩니다

## 사용법

```bash
# 기본 사용 (질문 파일만)
python main.py questions.txt

# Context tree 포함
python main.py questions.txt --context-tree context.json

# Context tree와 Input tree 모두 포함
python main.py questions.txt --context-tree context.json --input-tree input.json

# 출력 파일 지정
python main.py questions.txt --context-tree context.json --output results.json

# Copilot 건너뛰기 (API 키가 없을 때)
python main.py questions.txt --skip-copilot
```

## 예시 파일

- `example_questions.txt`: 질문 예시 (단순 형식)
- `example_questions_structured.txt`: 질문 예시 (구조화된 형식)
- `example_context_tree.json`: Context tree 예시
- `example_input_tree.json`: Input tree 예시 (Chapter 6, 7, 10 포함)
- `example_output_tree.json`: Output tree 예시 (결과 구조 참고)

## 주의사항

1. **API 키 보안**: `.env` 파일은 절대 Git에 커밋하지 마세요. `.gitignore`에 포함되어 있습니다.
2. **API 비용**: 각 API 호출마다 비용이 발생할 수 있습니다. 사용량을 모니터링하세요.
3. **Rate Limiting**: API 제공업체의 rate limit에 주의하세요. 많은 질문을 처리할 때는 적절한 대기 시간을 설정하세요.
4. **GitHub Copilot**: 
   - GitHub Copilot은 공개 API가 제한적이므로 OpenAI API를 사용합니다
   - `OPENAI_API_KEY`가 설정되어 있으면 자동으로 사용됩니다
   - `COPILOT_MODEL` 환경 변수로 모델을 설정할 수 있습니다 (기본: `gpt-3.5-turbo`)
   - ChatGPT와 다른 모델을 사용하여 비교 테스트가 가능합니다
   - `--skip-copilot` 옵션으로 명시적으로 건너뛸 수 있습니다
5. **응답 평가**: 현재는 응답이 있으면 "Correct Answer"로 분류합니다. 실제 정답과 비교하는 로직은 `classify_response()` 함수에서 구현해야 합니다.

