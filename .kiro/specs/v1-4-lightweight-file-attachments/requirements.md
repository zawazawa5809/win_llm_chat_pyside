# Requirements Document

## Introduction

本仕様は、v1.4「軽量ファイル添付（テキスト抽出＋要約/Q&A）」の実装に向けて、RAG や永続インデックスを用いずに、クライアント側のみで完結するファイル添付・テキスト抽出・要約/Q&A 機能の振る舞いと制約条件を定義する。

## Requirements

### Requirement 1: Lightweight file attachment and text extraction

**Objective:** As a knowledge worker using the LLM chat client, I want to attach PDF / text / Markdown files and have their text extracted on the client, so that I can reuse the content with the LLM without manual copy-paste and without building persistent indexes.

#### Acceptance Criteria

1. When the user selects or drags and drops a supported file（PDF, テキスト, Markdown）into a session, the system shall register the file in the session’s attachment list with at least filename and size, and display it in the UI.
2. When the user confirms attaching a supported file, the system shall extract text on the client side only, without sending the raw file binary to the LLM backend.
3. If the extracted text length exceeds a configurable threshold（例: 10,000〜20,000 文字）, the system shall warn the user and suggest splitting the file or narrowing the scope before sending the content to the LLM.
4. While attachments are present in a session, the system shall treat their extracted text as temporary data scoped to that session only and shall not build any persistent index or cross-session database based on that text.
5. Where an unsupported file type or a file exceeding the documented size/page limits is selected, the system shall reject the attachment and show a clear error message that explains the limitation and recommends manual splitting or alternative handling.

### Requirement 2: Summarization and Q&A over extracted text

**Objective:** As a knowledge worker, I want to request summaries and Q&A based on the extracted text of an attached file inside a session, so that I can quickly understand and query the document without leaving the chat flow.

#### Acceptance Criteria

1. When the user chooses an attached file and invokes a “summarize this file” action, the system shall send the extracted text plus an appropriate summarization prompt to the LLM and display the LLM’s response as a new assistant message in the current session.
2. When the user chooses an attached file and inputs a free-form question（例: 「このファイルについて〜」）, the system shall combine the question with the relevant extracted text and send it as a single request to the LLM, without storing the combined payload in any persistent index or cross-session storage.
