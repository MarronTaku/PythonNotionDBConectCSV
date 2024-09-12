import argparse
import pandas as pd
import re
import json
import requests
from datetime import datetime

# Notion APIの設定
NOTION_API_KEY = '???'  # Notion APIキー
DATABASE_ID = '???'  # NotionデータベースID
NOTION_API_URL = f'???'


# データをNotionに登録する
def add_to_notion(df: pd.DataFrame, prob2: str, prob3 : str) -> None:
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # 最新のNotion APIバージョンに合わせてください
    }
    
    # 正規表現を使って数字を抽出し、整数に変換
    if prob2 != None:
        prob2_intlist = list(map(int, re.findall(r'\d+', prob2)))
    else:
        prob2_intlist = []
    if prob3 != None:
        prob3_intlist = list(map(int, re.findall(r'\d+', prob3)))
    else:
        prob3_intlist = []
    
    for index, row in df.iterrows():
        no = int(row['No.'])
        correct = row['正誤']
        field_name = row['分野名']
        large_category = row['大分類']
        middle_category = row['中分類']
        citation_text = row['出典']
        url = row['URL']
        
        # 正誤判定による理解度を設定
        understanding_level = setting_understanding_degree(
            no, correct, prob2_intlist, prob3_intlist)
        
        print(understanding_level)

        # NotionDBに登録するデータの作成
        data = {
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "問題番号": {"number": no},
                "出典": {"title": [{"text": {"content": citation_text}}]},
                "理解度": {"number": understanding_level},
                "URL": {"url": url},
                "学習開始日": {"date": None},  # 空の値を設定
                "次の復習日": {"date": None},  # 空の値を設定
                "1回目": {"checkbox": False},
                "2回目": {"checkbox": False},
                "3回目": {"checkbox": False},
                "4回目": {"checkbox": False},
                "分野名": {"rich_text": [{"text": {"content": field_name}}]},
                "大分類": {"rich_text": [{"text": {"content": large_category}}]},
                "中分類": {"rich_text": [{"text": {"content": middle_category}}]}
            }
        }
        
        response = requests.post(
            NOTION_API_URL,
            headers=headers,
            data=json.dumps(data)
        )
        
        if response.status_code == 200:
            print(f"成功: {row['No.']}")
        else:
            print(f"エラー: {response.text}")


def save_csv(file_path: str, df) -> None:
    # 必要に応じて結果を新しいCSVファイルとして保存
    output_file_path = file_path.replace('.csv', '_processed.csv')
    df.to_csv(output_file_path, index=False)
    print(f"処理結果を保存しました: {output_file_path}")


def process_csv(file_path: str, encoding: str) -> pd.DataFrame:
    # CSVファイルを読み込む
    df = pd.read_csv(file_path, encoding=encoding)
    
    # 出典から文字列を抽出して処理
    def extract_and_update(source):
        # 正規表現を使って、ダブルクォートで囲まれた部分をすべて抽出
        matches = re.findall(r'"(.*?)"', source)
        
        if len(matches) == 2:
            # URLカラムにURLを追加
            url, citation = matches
            return url, citation
        
        # 正しく抽出できなかった場合は空の値を返す
        return '', source
    
    # 各行の出典を処理し、新しいURLカラムに追加
    for i, row in df.iterrows():
        url, updated_citation = extract_and_update(row['出典'])
        df.at[i, 'URL'] = url
        df.at[i, '出典'] = updated_citation
    
    # 処理結果を表示
    return df


# 正誤判定による理解度を設定
def setting_understanding_degree(prob_num: int, correct: str, prob2_list: list, prob3_list: list) -> int:
    understanding_level = 0
    
    # prob2とprob3に応じた理解度設定
    if correct == "○":
        understanding_level = 4
        # 正解した問題を理解度に応じて分ける
        if prob_num in prob2_list:
            understanding_level = 2
        if prob_num in prob3_list:
            understanding_level = 3
            print(understanding_level)
    elif correct == "×":
        understanding_level = 2
    else:
        understanding_level = None
        
    return understanding_level


def main():
    # コマンドライン引数のパーサーを設定
    parser = argparse.ArgumentParser(description='CSVファイルを読み込んで処理するプログラム')
    parser.add_argument('csv_file', type=str, help='読み込むCSVファイルのパス')
    parser.add_argument('--prob2', type=str, default=None, help='2:問題は不正解だったが、解説を読んだら理解ができた。')
    parser.add_argument('--prob3', type=str, default=None, help='3:問題に正解したが他の選択肢は理解できない。')
    parser.add_argument('--encoding', type=str, default='shift-jis', help='ファイルのエンコーディングを指定 (デフォルト: utf-8)')
    
    # 引数をパース
    args = parser.parse_args()
    
    # CSVファイルを加工する
    df = process_csv(args.csv_file, args.encoding)
    
    # csvファイルの保存
    #save_csv(file_path="output/test.csv", df=df)
    
    # Notionデータベースカラムを追加する
    add_to_notion(df=df, prob2=args.prob2, prob3=args.prob3)
    

if __name__ == "__main__":
    main()