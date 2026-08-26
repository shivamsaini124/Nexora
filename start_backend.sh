#!/bin/bash

cd Database\ Infra/
docker compose up -d

sleep 3

cd ../Backend
uvicorn app.main:app --reload