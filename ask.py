#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ask.py – 日本語LLM（ELYZA）のCLIクライアント

#.env の ELYZA_MODEL_PATH を優先的に読み込み、
#–model オプションでパスを上書き可能
#–stream でストリーミング出力対応
"""

import argparse
import os
from dotenv import load_dotenv
from llama_cpp import Llama
import multiprocessing

def main():
    # .env から環境変数をロード
    load_dotenv()

    # 引数定義
    default_model = os.getenv(
        "ELYZA_MODEL_PATH",
        "models/elyza7b/ELYZA-japanese-Llama-2-7b-instruct.Q4_0.gguf"
    )
    parser = argparse.ArgumentParser(
        description="ELYZA 日本語LLMにプロンプトを投げるCLI"
    )
    parser.add_argument(
        "--model",
        default=default_model,
        help="モデルファイルのパス (.env の ELYZA_MODEL_PATH を優先)"
    )
    parser.add_argument(
        "prompt",
        help="日本語で質問を入力"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=64,
        help="生成する最大トークン数"
    )
    parser.add_argument(
        "--temp",
        type=float,
        default=0.7,
        help="生成の多様性を制御する温度パラメータ"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="ストリーミングモードで逐次出力"
    )
    args = parser.parse_args()

    # モデルロード（CPU全コアを利用）
    llm = Llama(
        model_path=args.model,
        n_ctx=1024,
        n_threads=multiprocessing.cpu_count(),
        verbose=False
    )

    # Instruct フォーマットを付与
    inj_prompt = f"### 指示\n{args.prompt}\n### 応答\n"

    # 実行 & 出力
    if args.stream:
        for chunk in llm(
            inj_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temp,
            stream=True
        ):
            print(chunk["choices"][0]["text"], end="", flush=True)
        print()
    else:
        res = llm(
            inj_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temp
        )
        print(res["choices"][0]["text"].strip())


if __name__ == "__main__":
    main()
