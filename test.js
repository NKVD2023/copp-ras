const fs = require('fs');
const html = fs.readFileSync('/home/copp-admin/copp-ras/app/templates/constructor.html', 'utf-8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (scriptMatch) {
    const script = scriptMatch[1];
    try {
        require('vm').Script(script);
        console.log("No syntax errors in JS!");
    } catch (e) {
        console.error("Syntax Error:", e);
    }
}
