#!/bin/bash

MODEL="gemma3:4b"

usage() {
    echo "Usage: ollama.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start Ollama server"
    echo "  stop        Stop Ollama server"
    echo "  status      Check server status and loaded models"
    echo "  chat        Start chatting with $MODEL"
    echo "  unload      Unload model from RAM"
    echo ""
}

case "$1" in
    start)
        echo "Starting Ollama server..."
        sudo systemctl start ollama
        sudo systemctl status ollama --no-pager
        ;;
    stop)
        echo "Stopping Ollama server..."
        ollama stop $MODEL 2>/dev/null
        sudo systemctl stop ollama
        echo "Ollama stopped."
        ;;
    status)
        echo "=== Ollama server ==="
        sudo systemctl status ollama --no-pager
        echo ""
        echo "=== Loaded models ==="
        ollama ps
        echo ""
        echo "=== Downloaded models ==="
        ollama list
        echo ""
        echo "=== RAM ==="
        free -h
        ;;
    chat)
        echo "Starting chat with $MODEL..."
        ollama run $MODEL
        ;;
    unload)
        echo "Unloading $MODEL from RAM..."
        ollama stop $MODEL
        echo "Done."
        ;;
    *)
        usage
        ;;
esac
