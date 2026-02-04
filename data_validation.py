# =============================================================================
# data_validator.py - 검증 메서드 클래스
# =============================================================================
import pandas as pd 
import operator

class DataValidator:
    def __init__(self, df):
        self.df = df 
        
    def _add_error(self, idx, col, error_col_name):
        """에러 컬럼 생성

        Args:
            idx (int): 에러가 발생한 인덱스
            col (int): 에러가 발생한 컬럼
            error_col_name (str): 에러명
        """
        if error_col_name not in self.df.columns:
            self.df[error_col_name] = ''
            
        self.df.loc[idx, error_col_name] = self.df.loc[idx, error_col_name].apply(
                lambda x: col if x == '' else f"{x},{col}"
            )
        
    def miss_value(self, columns):  # df 파라미터 제거
        """결측값 확인

        Args:
            columns (list[str]): 분석 할 문항명 
        """
            
        for col in columns:
            idx = self.df[self.df[col].isna()].index  # self.df 사용
            self._add_error(idx, col, 'Error_결측')
            
    def between_a_b(self, columns, min, max):
        """범위 내의 값 확인 
        ex) 1~5 까지의 문항인데 6이 있을때 

        Args:
            columns (_DataFrame): 분석 할 문항명
            min (int): 최솟값
            max (int): 최댓값
        """

        for col in columns:
            idx = self.df[self.df[col].notna() & ~self.df[col].between(min, max)].index
            self._add_error(idx, col, 'Error_범위')

    def multiple_response_check(self, columns):
        """단일 응답 컬럼에서 다중 응답인 케이스 찾기"""
        for col in columns:
            # 숫자인 경우 정수로 변환 후 문자열로, 아닌 경우 그대로 문자열로
            def clean_convert(x):
                if pd.isna(x):
                    return ""
                try:
                    # 소수점이 .0인 경우 정수로 변환
                    if float(x) == int(float(x)):
                        return str(int(float(x)))
                    else:
                        return str(x)
                except:
                    return str(x)
            
            condition = self.df[col].apply(clean_convert).str.len() > 1
            idx = self.df[condition].index
            self._add_error(idx, col, 'Error_중복응답')
        
    def early_end(self, column, value):
        """문항에서 특정 번호 선택하면 설문 종료(단일 문항만 가능)
        
        ex) Q2에서 3을 선택했으면 설문 종료(Q3부터 모두 결측)

        Args:
            column (str): 분석 할 문항명 (단일 컬럼)
            value (str/int): 조기종료 값
        """
        condition1 = self.df[column] == value
        col_position = self.df.columns.get_loc(column) + 1
        
        # Error 컬럼들 제외하고 원본 데이터 컬럼들만 확인
        original_cols = [col for col in self.df.columns if not col.startswith('Error_')]
        original_df = self.df[original_cols]
        
        # 원본 데이터에서 해당 컬럼 이후 위치 찾기
        original_col_position = original_df.columns.get_loc(column) + 1
        
        # 원본 데이터의 이후 컬럼들이 모두 결측인지 확인
        all_missing_after = original_df.iloc[:, original_col_position:].isna().all(axis=1)
        
        invalid_early_end = condition1 & ~all_missing_after
        idx = self.df[invalid_early_end].index
        
        self._add_error(idx, column, 'Error_조기종료')

    def skip_pattern(self, start_col, value, end_col):
        """특정 문항에서 특정 값을 선택했을 때 다른 문항으로 이동 
            건너뛰어야 할 문항들에 응답이 있으면 에러
        
            ex) Q3에서 2를 선택하면 Q6으로 이동 (Q4, Q5는 건너뛰기)
        
        Args:
            start_col (str): 시작 문항
            value (int/str): 선택 값
            end_col (str): 종료 문항 
        """
        # 시작 문항에서 스킵 조건 값을 선택한 행들
        con1 = self.df[start_col] == value
        
        # 건너뛰어야 할 문항들에 값이 하나라도 있는지 확인
        con2 = self.df.iloc[:, 
                            self.df.columns.get_loc(start_col)+1:
                            self.df.columns.get_loc(end_col)
                            ].notna().any(axis=1)

        # 에러 케이스 인덱스
        idx = self.df[con1 & con2].index

        self._add_error(idx, start_col, 'Error_문항스킵')
        

    def same_value(self, col1, col2):
        """두 문항의 값이 같으면 안 되는 검증

        Args:
            col1 (str): 비교문항 1번
            col2 (str): 비교문항 2번
        """
        condition = (self.df[col1] == self.df[col2])
        idx = self.df[condition].index
        self._add_error(idx, col1, 'Error_동일값금지')
            
    def comparison_columns(self, col1, col2, method):
        """두 문항 간 크기 비교 검증
        
        Args:
            col1 (str): 비교 문항1
            col2 (str): 비교 문항2  
            method (str): 비교 연산자 ('<', '<=', '>', '>=', '==', '!=')
        """
        # 미만
        if method == '<(작다)':
            condition = self.df[col1] < self.df[col2]
        # 이하
        elif method == '<=(작거나같다)':
            condition = self.df[col1] <= self.df[col2]
        # 초과
        elif method == '>(크다)':
            condition = self.df[col1] > self.df[col2]
        # 이상
        elif method == '>=(크거나같다)':
            condition = self.df[col1] >= self.df[col2]
        # 같음
        elif method == '==(같다)':
            condition = self.df[col1] == self.df[col2]
        # 같지 않음
        elif method == '!=(다르다)':
            condition = self.df[col1] != self.df[col2]
        else:
            return  # 잘못된 method인 경우
            
        idx = self.df[condition].index
        self._add_error(idx, col1, f'Error_문항크기비교')
        
        
    def comparison_value(self, col, val, method):
        """문항 값과 특정 값 비교 검증
        
        Args:
            col (str): 비교할 문항
            val (int/float): 비교할 값
            method (str): 비교 연산자 ('<', '<=', '>', '>=', '==', '!=')
        """
        # 미만
        if method == '<(작다)':
            condition = self.df[col] < val
        # 이하
        elif method == '<=(작거나같다)':
            condition = self.df[col] <= val
        # 초과
        elif method == '>(크다)':
            condition = self.df[col] > val
        # 이상
        elif method == '>=(크거나같다)':
            condition = self.df[col] >= val
        # 같음
        elif method == '==(같다)':
            condition = self.df[col] == val
        # 같지 않음
        elif method == '!=(다르다)':
            condition = self.df[col] != val
        else:
            return
            
        idx = self.df[condition].index
        self._add_error(idx, col, f'Error_문항과값비교')
        
        
    def require_missing(self, col1, val, col2):
        """어떤 문항에서 어떤 값을 선택했을때 다른 문항이 결측인 경우 찾기
        
        Args:
            col1 (str): 조건 문항
            val (list): 조건 값
            col2 (str): 결측 확인 문항
        """
        idx = self.df[(self.df[col1].isin(val)) & self.df[col2].isna()].index
        self._add_error(idx, col1, 'Error_조건부결측')


    def require_value(self, col1, val, col2):
        """어떤 문항에서 어떤 값을 선택했을때 다른 문항에 값이 있을 경우 찾기
        
        Args:
            col1 (str): 조건 문항
            val (list): 조건 값
            col2 (str): 값 확인 문항
        """
        idx = self.df[(self.df[col1].isin(val)) & self.df[col2].notna()].index
        self._add_error(idx, col1, 'Error_조건부필수')
        
        
    def conditional_mapping(self, col1, val1, col2, val2):
        """조건1일 때 조건2인 케이스 찾기
        
        - Q1이 2일 때 Q2가 1,5인 케이스 → val2=[1,5]
        
        Args:
            col1 (str): 조건 문항
            val1 (list): 조건 값들
            col2 (str): 확인 문항
            val2 (list): 확인할 값들
        """
        condition = self.df[col1].isin(val1) & self.df[col2].isin(val2)
        idx = self.df[condition].index
        self._add_error(idx, col1, 'Error_조건부로직')
        
        
    def comparison(self, ct: dict):
        """컬럼, 상수 간의 산술 및 비교 연산 

        Args:
            ct (dict): 좌변, 비교연산자, 우변 정보

        """
        
        # 산술 연산자 매핑
        ops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv
        }
        
        # 비교 연산자 매핑
        compare_ops = {
            '>': operator.gt,
            '<': operator.lt,
            '>=': operator.ge,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne
        }
        
        # 표현식 계산
        def calc(expr: list) -> pd.Series:
            result = None
            current_op = None
            
            for item in expr:
                if item in ops:
                    current_op = item
                else:
                    if item in self.df.columns:
                        value = self.df[item].copy()
                    else:
                        value = pd.Series([float(item)] * len(self.df))
                    
                    if result is None:
                        result = value
                    else:
                        result = ops[current_op](result, value)
            
            return result
        
        # 좌변, 우변 계산 후 비교
        left_result = calc(ct['left'])
        right_result = calc(ct['right'])
        mask = compare_ops[ct['compare']](left_result, right_result)
        
        idx = self.df[mask].index
        
        # 에러 표시할 컬럼 
        right_columns = list(filter(lambda x: x not in ops, ct['right']))
        
        self._add_error(idx, right_columns[0], 'Error_문항값통합')
        
        
        
    def exclusive_multi_value(self, cols, val):
        """다중응답 문항 중에서 특정 값이 있으면 다른값은 모두 결측이여야하는데 아닌것 찾음
        
        Args:
            cols (list): 조건 문항
            val (int): 조건 값
        """
        
        mask_val = (self.df[cols] == val).any(axis=1)  

        mask = mask_val & ((self.df[cols] != val) & self.df[cols].notna()).any(axis=1) 

        idx = self.df[mask].index

        self._add_error(idx, cols[0], 'Error_특정값존재(다중응답)')