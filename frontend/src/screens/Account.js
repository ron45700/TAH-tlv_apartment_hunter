import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// Sign-in, sign-up with a key, and the password change (PHASE_3.md 3.7 (f)). Each refusal of 3.5 in
// words: a wrong username or password (one answer for both), the delay with its seconds, a disabled
// account. Sign-up has no "use my current filter" box (#336): a new user starts with #268's defaults.
// The forced change is the only screen reachable while it is due (Gate C, `Session`); the same form
// serves a change the user chooses (from the preferences page).
import { useEffect, useState } from 'react';
import { ApiError, api } from '../api';
import { navigate } from '../route';
const MIN_PASSWORD = 8; // #262
function words(error) {
    if (!(error instanceof ApiError))
        return 'משהו השתבש. נסו שוב.';
    switch (error.refusal) {
        case 'wrong':
            return 'שם המשתמש או הסיסמה שגויים.';
        case 'disabled':
            return 'החשבון הושבת. פנו למנהל האתר.';
        case 'key_not_usable':
            return 'קוד ההזמנה לא תקף: הוא שגוי, כבר נוצל או בוטל.';
        case 'username_taken':
            return 'שם המשתמש תפוס. בחרו שם אחר.';
        case 'username_invalid':
            return 'שם המשתמש לא עומד בכללים שמתחת לשדה.';
        case 'password_too_short':
            return `הסיסמה קצרה מדי: לפחות ${MIN_PASSWORD} תווים.`;
        case 'changed':
            return 'הסיסמה שונתה בינתיים. התחברו שוב.';
    }
    if (error.status === 0)
        return 'אין חיבור לאתר. בדקו שהוא פועל ונסו שוב.';
    return 'משהו השתבש. נסו שוב.';
}
function go(path) {
    return (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0)
            return;
        event.preventDefault();
        navigate(path);
    };
}
function Screen({ title, lead, children }) {
    return (_jsx("main", { className: "shell screen", children: _jsxs("div", { className: "formcard", children: [_jsx("h1", { children: title }), lead && _jsx("p", { className: "lead", children: lead }), children] }) }));
}
function TextField({ id, label, value, onChange, autoComplete, type = 'text', hint, }) {
    return (_jsxs("div", { className: "tfield", children: [_jsx("label", { htmlFor: id, children: label }), _jsx("input", { id: id, name: id, type: type, dir: "ltr", value: value, autoComplete: autoComplete, autoCapitalize: "none", spellCheck: false, "aria-describedby": hint ? `${id}-hint` : undefined, onChange: (event) => onChange(event.target.value) }), hint && (_jsx("p", { className: "tfield-hint", id: `${id}-hint`, children: hint }))] }));
}
function Problem({ text }) {
    return (_jsx("p", { className: "formerror", role: "alert", children: text }));
}
/** The seconds left of a delay, counting down; 0 when there is none. */
function useCountdown() {
    const [until, setUntil] = useState(0);
    const [now, setNow] = useState(() => Date.now());
    useEffect(() => {
        if (until <= now)
            return;
        const timer = window.setTimeout(() => setNow(Date.now()), 250);
        return () => window.clearTimeout(timer);
    }, [until, now]);
    const start = (seconds) => {
        const at = Date.now();
        setNow(at);
        setUntil(at + seconds * 1000);
    };
    return [Math.max(0, Math.ceil((until - now) / 1000)), start];
}
export function SignIn({ onSignedIn }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [problem, setProblem] = useState(null);
    const [busy, setBusy] = useState(false);
    const [wait, delay] = useCountdown();
    const submit = async (event) => {
        event.preventDefault();
        if (busy || wait)
            return;
        setBusy(true);
        setProblem(null);
        try {
            const { user } = await api.signIn(username.trim(), password);
            onSignedIn(user);
        }
        catch (error) {
            setPassword('');
            if (error instanceof ApiError && error.refusal === 'delayed')
                delay(error.retryAfter ?? 30);
            else
                setProblem(words(error));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs(Screen, { title: "\u05D4\u05EA\u05D7\u05D1\u05E8\u05D5\u05EA", children: [_jsxs("form", { onSubmit: submit, noValidate: true, children: [_jsx(TextField, { id: "si-user", label: "\u05E9\u05DD \u05DE\u05E9\u05EA\u05DE\u05E9", value: username, onChange: setUsername, autoComplete: "username" }), _jsx(TextField, { id: "si-pass", label: "\u05E1\u05D9\u05E1\u05DE\u05D4", type: "password", value: password, onChange: setPassword, autoComplete: "current-password" }), _jsx(Problem, { text: wait ? `יותר מדי ניסיונות שגויים. אפשר לנסות שוב בעוד ${wait} שניות.` : problem }), _jsx("button", { className: "mainbtn", type: "submit", disabled: busy || wait > 0 || !username || !password, children: busy ? 'מתחבר…' : 'התחברות' })] }), _jsxs("p", { className: "formfoot", children: ["\u05D0\u05D9\u05DF \u05DC\u05DB\u05DD \u05D7\u05E9\u05D1\u05D5\u05DF?", ' ', _jsx("a", { href: "/sign-up", onClick: go('/sign-up'), children: "\u05D4\u05E8\u05E9\u05DE\u05D4 \u05E2\u05DD \u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4" })] })] }));
}
export function SignUp({ onSignedIn }) {
    const [key, setKey] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [again, setAgain] = useState('');
    const [problem, setProblem] = useState(null);
    const [busy, setBusy] = useState(false);
    const submit = async (event) => {
        event.preventDefault();
        if (busy)
            return;
        if (password.length < MIN_PASSWORD)
            return setProblem(`הסיסמה קצרה מדי: לפחות ${MIN_PASSWORD} תווים.`);
        if (password !== again)
            return setProblem('שתי הסיסמאות שונות זו מזו.');
        setBusy(true);
        setProblem(null);
        try {
            const { user } = await api.signUp(key.trim(), username.trim(), password);
            onSignedIn(user);
        }
        catch (error) {
            setProblem(words(error));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs(Screen, { title: "\u05D4\u05E8\u05E9\u05DE\u05D4", lead: "\u05D4\u05D4\u05E8\u05E9\u05DE\u05D4 \u05D1\u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4 \u05D0\u05D9\u05E9\u05D9, \u05D7\u05D3-\u05E4\u05E2\u05DE\u05D9. \u05D0\u05D7\u05E8\u05D9 \u05D4\u05D4\u05E8\u05E9\u05DE\u05D4 \u05D1\u05D5\u05D7\u05E8\u05D9\u05DD \u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05D1\u05E2\u05DE\u05D5\u05D3 \u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA.", children: [_jsxs("form", { onSubmit: submit, noValidate: true, children: [_jsx(TextField, { id: "su-key", label: "\u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4", value: key, onChange: setKey, autoComplete: "off" }), _jsx(TextField, { id: "su-user", label: "\u05E9\u05DD \u05DE\u05E9\u05EA\u05DE\u05E9", value: username, onChange: setUsername, autoComplete: "username", hint: "\u05D0\u05D5\u05EA\u05D9\u05D5\u05EA \u05D1\u05D0\u05E0\u05D2\u05DC\u05D9\u05EA, \u05E1\u05E4\u05E8\u05D5\u05EA, \u05D5\u05D2\u05DD _ . -, \u05D1\u05D9\u05DF 3 \u05DC-32 \u05EA\u05D5\u05D5\u05D9\u05DD. \u05D0\u05D9 \u05D0\u05E4\u05E9\u05E8 \u05DC\u05E9\u05E0\u05D5\u05EA \u05D0\u05D5\u05EA\u05D5 \u05D0\u05D7\u05E8 \u05DB\u05DA." }), _jsx(TextField, { id: "su-pass", label: "\u05E1\u05D9\u05E1\u05DE\u05D4", type: "password", value: password, onChange: setPassword, autoComplete: "new-password", hint: `לפחות ${MIN_PASSWORD} תווים.` }), _jsx(TextField, { id: "su-again", label: "\u05D4\u05E1\u05D9\u05E1\u05DE\u05D4 \u05E9\u05D5\u05D1", type: "password", value: again, onChange: setAgain, autoComplete: "new-password" }), _jsx(Problem, { text: problem }), _jsx("button", { className: "mainbtn", type: "submit", disabled: busy || !key || !username || !password || !again, children: busy ? 'נרשם…' : 'הרשמה' })] }), _jsxs("p", { className: "formfoot", children: ["\u05DB\u05D1\u05E8 \u05D9\u05E9 \u05DC\u05DB\u05DD \u05D7\u05E9\u05D1\u05D5\u05DF?", ' ', _jsx("a", { href: "/sign-in", onClick: go('/sign-in'), children: "\u05D4\u05EA\u05D7\u05D1\u05E8\u05D5\u05EA" })] })] }));
}
export function PasswordScreen({ forced, onChanged, onSignOut, }) {
    const [current, setCurrent] = useState('');
    const [next, setNext] = useState('');
    const [again, setAgain] = useState('');
    const [problem, setProblem] = useState(null);
    const [busy, setBusy] = useState(false);
    const [done, setDone] = useState(false);
    const submit = async (event) => {
        event.preventDefault();
        if (busy)
            return;
        if (next.length < MIN_PASSWORD)
            return setProblem(`הסיסמה החדשה קצרה מדי: לפחות ${MIN_PASSWORD} תווים.`);
        if (next !== again)
            return setProblem('שתי הסיסמאות החדשות שונות זו מזו.');
        setBusy(true);
        setProblem(null);
        try {
            const { user } = await api.password(current, next);
            setCurrent('');
            setNext('');
            setAgain('');
            setDone(true);
            onChanged(user);
        }
        catch (error) {
            const wrong = error instanceof ApiError && error.refusal === 'wrong';
            setProblem(wrong ? (forced ? 'הסיסמה הזמנית שגויה.' : 'הסיסמה הנוכחית שגויה.') : words(error));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs(Screen, { title: forced ? 'בחירת סיסמה חדשה' : 'שינוי סיסמה', lead: forced ? 'הסיסמה שלכם אופסה. כדי להמשיך, בחרו סיסמה חדשה.' : 'אחרי השינוי, החיבורים שלכם במכשירים אחרים יסתיימו.', children: [done && !forced ? (_jsx("p", { className: "formok", role: "status", children: "\u05D4\u05E1\u05D9\u05E1\u05DE\u05D4 \u05E9\u05D5\u05E0\u05EA\u05D4." })) : (_jsxs("form", { onSubmit: submit, noValidate: true, children: [_jsx(TextField, { id: "pw-current", label: forced ? 'הסיסמה הזמנית' : 'הסיסמה הנוכחית', type: "password", value: current, onChange: setCurrent, autoComplete: "current-password" }), _jsx(TextField, { id: "pw-new", label: "\u05E1\u05D9\u05E1\u05DE\u05D4 \u05D7\u05D3\u05E9\u05D4", type: "password", value: next, onChange: setNext, autoComplete: "new-password", hint: `לפחות ${MIN_PASSWORD} תווים.` }), _jsx(TextField, { id: "pw-again", label: "\u05D4\u05E1\u05D9\u05E1\u05DE\u05D4 \u05D4\u05D7\u05D3\u05E9\u05D4 \u05E9\u05D5\u05D1", type: "password", value: again, onChange: setAgain, autoComplete: "new-password" }), _jsx(Problem, { text: problem }), _jsx("button", { className: "mainbtn", type: "submit", disabled: busy || !current || !next || !again, children: busy ? 'שומר…' : 'שמירת הסיסמה' })] })), _jsx("p", { className: "formfoot", children: forced ? (_jsx("button", { type: "button", className: "linkbtn", onClick: onSignOut, children: "\u05D4\u05EA\u05E0\u05EA\u05E7" })) : (_jsx("a", { href: "/preferences", onClick: go('/preferences'), children: "\u05D7\u05D6\u05E8\u05D4 \u05DC\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA" })) })] }));
}
