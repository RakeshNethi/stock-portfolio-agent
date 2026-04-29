# Architecture

This document describes the high-level architecture of the Stock Portfolio Agent.

## Overview
The Stock Portfolio Agent is an autonomous AI agent built to monitor a stock portfolio, deliver daily briefings, track earnings, run technical analysis, and generate actionable recommendations. It is designed to run serverless on Google Cloud Platform.

## System Components

1. **Google Cloud Scheduler**: Triggers the Cloud Run Job at specified times (Morning and Evening).
2. **Google Cloud Run Jobs**: Executes the agent within a Python container.
3. **LangGraph Agent**: The core workflow engine that orchestrates the data collection, analysis, and synthesis.
4. **Market Data Collector**: Fetches current prices and market summary (via Alpha Vantage).
5. **Technical Analyzer**: Computes technical indicators like RSI, MACD, Moving Averages, and Bollinger Bands.
6. **Earnings Tracker**: Retrieves upcoming earnings events and recent surprises (via Financial Modeling Prep).
7. **LLM Synthesizer**: Utilizes Gemini 2.0 Flash to synthesize the data into a cohesive briefing.
8. **Notification Dispatcher**: Sends the briefing via Email (SendGrid) and Telegram.

## Agent Graph Structure

The LangGraph workflow consists of the following sequence:
- `load_portfolio` -> `fetch_market_data`
- `fetch_market_data` -> `run_technical_analysis` -> `check_earnings` -> `fetch_news_sentiment`
- (`run_technical_analysis`, `check_earnings`, `fetch_news_sentiment`) -> `synthesize_briefing`
- `synthesize_briefing` -> `quality_check` (retries if necessary) -> `send_notifications`

## Cost Efficiency
The system relies on free tiers of various services (Alpha Vantage, FMP, Finnhub, SendGrid, Telegram) and serverless execution (Cloud Run), ensuring costs remain negligible.
