document.addEventListener('DOMContentLoaded', () => {
    // --- UI 引用 ---
    const landingPage = document.getElementById('landing-page');
    const chatPage = document.getElementById('chat-page');
    const getStartBtn = document.getElementById('get-start-btn');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatHistory = document.getElementById('chat-history');

    // 机器人动画相关
    const robotBody = document.querySelector('.robot-body');
    const robotFace = document.getElementById('robot-face');
    const robotStatusText = document.getElementById('robot-status-text');

    // 会话与建议
    const openingCard = document.getElementById('opening-card');
    const suggestions = document.getElementById('suggestions');
    const sessionList = document.getElementById('session-list');
    const newChatBtn = document.getElementById('new-chat-btn');

    // 模态框相关
    const statsBtn = document.getElementById('stats-btn');
    const statsModal = document.getElementById('stats-modal');
    const closeModalSpan = document.querySelector('.close-btn');
    const statsTableBody = document.querySelector('#stats-table tbody');

    // --- 表情定义 ---
    const EMOTIONS = {
        idle: ['^ ◡ ^', '• ◡ •', '> ◡ <', 'º ◡ º', '¬ ◡ ¬'],
        thinking: ['o . o', '. . .', '* . *', 'o_o'],
        happy: ['^ ▽ ^', '≧◡≦', '★ ◡ ★', 'UwU'],
        talking: ['● ﹏ ●', '▼ ◡ ▼', '● 3 ●'],
        sleep: ['- . -', 'u . u', 'z z Z']
    };

    let currentSessionId = 'default';
    let isInteracting = false;

    // --- 1. 交互动画逻辑 ---

    const robotWrapper = document.getElementById('header-robot');
    if (robotWrapper) {
        robotWrapper.addEventListener('click', () => {
            if (isInteracting) return;
            // 触发 CSS 动画
            robotBody.classList.remove('anim-boing');
            void robotBody.offsetWidth; // 强制重绘
            robotBody.classList.add('anim-boing');
            setFace(pickRandom(EMOTIONS.happy));
            setTimeout(() => { if(!isInteracting) setFace(EMOTIONS.idle[0]); }, 1500);
        });
    }

    // 自动眨眼/空闲动画
    setInterval(() => {
        if (isInteracting) return;
        if (Math.random() < 0.2) {
            setFace(pickRandom(EMOTIONS.idle));
        } else {
            setFace(EMOTIONS.idle[0]);
        }
    }, 3000);

    function setFace(face) {
        if(robotFace) robotFace.textContent = face;
    }

    function pickRandom(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    // --- 2. 聊天核心逻辑 ---

    // 点击建议气泡
    if(suggestions) {
        suggestions.addEventListener('click', (e) => {
            if (e.target.classList.contains('chip')) {
                const text = e.target.textContent.replace(/^[^\s]+\s/, ''); // 去掉emoji
                userInput.value = text;
                sendMessage();
            }
        });
    }

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        userInput.value = '';
        if (openingCard) openingCard.style.display = 'none';

        // 机器人进入思考状态
        isInteracting = true;
        setFace(pickRandom(EMOTIONS.thinking));
        if(robotStatusText) robotStatusText.textContent = 'Thinking deeply...';

        const thinkingId = appendThinking();

        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, session_id: currentSessionId })
        })
            .then(res => res.json())
            .then(data => {
                removeThinking(thinkingId);

                // 机器人说话状态
                setFace(pickRandom(EMOTIONS.talking));
                if(robotStatusText) robotStatusText.textContent = 'Typing...';

                if (data.error) {
                    appendMessage('bot', '哎呀，我的线缆好像打结了... (网络错误)');
                } else {
                    appendMessage('bot', data.response);
                }

                // 恢复空闲
                setTimeout(() => {
                    isInteracting = false;
                    setFace(EMOTIONS.idle[0]);
                    if(robotStatusText) robotStatusText.textContent = 'AI Consultant Ready';
                }, 2000);
            })
            .catch(err => {
                removeThinking(thinkingId);
                appendMessage('bot', 'Connection failed.');
                isInteracting = false;
                console.error(err);
            });
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // --- 3. UI 辅助函数 ---

    getStartBtn.addEventListener('click', () => {
        landingPage.style.opacity = '0';
        setTimeout(() => {
            landingPage.classList.remove('active');
            chatPage.classList.add('active');
            refreshSessions();
            switchSession(currentSessionId);
        }, 400);
    });

    function appendMessage(sender, text) {
        const div = document.createElement('div');
        div.classList.add('message', sender === 'user' ? 'user-msg' : 'bot-msg');
        // 简单的Markdown bold处理
        div.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
        chatHistory.appendChild(div);
        scrollToBottom();
    }

    function appendThinking() {
        const div = document.createElement('div');
        div.id = 'thinking-bubble';
        div.classList.add('message', 'bot-msg');
        div.style.fontStyle = 'italic';
        div.style.color = '#888';
        div.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        chatHistory.appendChild(div);
        scrollToBottom();
        return 'thinking-bubble';
    }

    function removeThinking(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        const scrollArea = document.getElementById('chat-container');
        if(scrollArea) {
            scrollArea.scrollTo({
                top: scrollArea.scrollHeight,
                behavior: 'smooth'
            });
        }
    }

    // --- 4. 会话管理逻辑 ---

    function refreshSessions() {
        fetch('/sessions').then(r => r.json()).then(data => {
            sessionList.innerHTML = '';
            data.sessions.forEach(s => {
                const li = document.createElement('li');
                li.className = 'session-item';
                if (s.id === currentSessionId) li.classList.add('active-session');

                const nameSpan = document.createElement('span');
                nameSpan.textContent = s.name;
                li.appendChild(nameSpan);

                // --- 修改开始：不再判断 s.id !== 'default'，给所有会话都加删除按钮 ---
                const del = document.createElement('span');
                del.textContent = '×';
                del.style.marginLeft = '10px';
                del.style.cursor = 'pointer';
                del.style.color = '#aaa'; // 加个颜色区分
                del.onmouseover = () => del.style.color = 'red';
                del.onmouseout = () => del.style.color = '#aaa';

                del.onclick = (e) => {
                    e.stopPropagation();
                    deleteSession(s.id);
                };
                li.appendChild(del);
                // --- 修改结束 ---

                li.onclick = () => switchSession(s.id);
                sessionList.appendChild(li);
            });
        });
    }

    function deleteSession(id) {
        if (!confirm('确定要删除这个会话吗？')) return;

        fetch(`/sessions/${id}`, {method: 'DELETE'}).then(() => {
            // 如果删除的是当前正在查看的会话，需要决定跳转到哪里
            if (currentSessionId === id) {
                fetch('/sessions').then(r => r.json()).then(data => {
                    if (data.sessions.length > 0) {
                        // 还有其他会话，跳到第一个
                        currentSessionId = data.sessions[0].id;
                        refreshSessions();
                        switchSession(currentSessionId);
                    } else {
                        // 会话全删光了，自动新建一个
                        fetch('/new_session', {method: 'POST'}).then(r => r.json()).then(d => {
                            currentSessionId = d.session_id;
                            refreshSessions();
                            switchSession(currentSessionId);
                        });
                    }
                });
            } else {
                // 删除的不是当前的，直接刷新列表即可
                refreshSessions();
            }
        });
    }

    newChatBtn.addEventListener('click', () => {
        fetch('/new_session', {method:'POST'}).then(r=>r.json()).then(d => {
            currentSessionId = d.session_id;
            refreshSessions();
            switchSession(currentSessionId);
        });
    });

    function switchSession(id) {
        currentSessionId = id;
        refreshSessions();
        fetch(`/session_history?session_id=${id}`).then(r=>r.json()).then(d => {
            chatHistory.innerHTML = '';
            // 显示/隐藏开场白
            if (!d.chat_history || d.chat_history.length === 0) {
                if (openingCard) openingCard.style.display = 'block';
            } else {
                if (openingCard) openingCard.style.display = 'none';
                d.chat_history.forEach(msg => appendMessage(msg.sender, msg.text));
            }
        });
    }

    // --- 5. 模态框逻辑 (思维链) ---

    if (statsBtn && statsModal) {
        statsBtn.addEventListener('click', () => {
            statsModal.style.display = 'block';
            loadThoughts();
        });

        closeModalSpan.addEventListener('click', () => {
            statsModal.style.display = 'none';
        });

        window.addEventListener('click', (event) => {
            if (event.target === statsModal) {
                statsModal.style.display = 'none';
            }
        });
    }

    function loadThoughts() {
        fetch(`/thoughts?session_id=${currentSessionId}`)
            .then(r => r.json())
            .then(data => {
                statsTableBody.innerHTML = '';
                if (!data.history || data.history.length === 0) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td colspan="6" style="text-align:center;color:#999;">暂无思维链记录</td>`;
                    statsTableBody.appendChild(tr);
                    return;
                }
                // 倒序显示，最新的在上面
                [...data.history].reverse().forEach(t => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${t.stage || '-'}</td>
                        <td>${t.mood || '-'}</td>
                        <td>${t.needs || '-'}</td>
                        <td>${t.change_tools || '-'}</td>
                        <td>${t.supervision || '-'}</td>
                        <td>${t.notes || '-'}</td>
                    `;
                    statsTableBody.appendChild(tr);
                });
            })
            .catch(e => console.error("加载思维链失败", e));
    }

});