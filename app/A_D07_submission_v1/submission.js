// Format-only usability revision. Never changes an answer or submission action.
(() => {
  const outputs = document.getElementById('outputs');
  const citations = document.getElementById('citations');
  const button = document.getElementById('submit');
  const original = document.getElementById('error');
  if (!outputs || !citations || !button || !original) return;
  outputs.closest('label').firstChild.textContent = 'outputs（按任务要求填写完整JSON，使用英文直双引号；不能并排粘贴多个数组）';
  outputs.placeholder = '{"字段名": null}';
  citations.closest('label').firstChild.textContent = '源码依据（每行填写 文件路径:起始行-结束行，不粘贴源码正文）';
  const message = document.createElement('p');
  message.id = 'submission-format-error';
  message.setAttribute('role', 'alert');
  message.setAttribute('aria-live', 'polite');
  message.hidden = true;
  button.before(message);
  const copyError = () => {
    const text = original.textContent.trim();
    if (!text) { message.hidden = true; message.textContent = ''; return; }
    const jsonError = /JSON|Unexpected|Expected|position|unterminated/i.test(text);
    message.textContent = jsonError
      ? '未保存：outputs格式不是合法JSON。请使用英文直双引号，按任务要求把各字段写在同一对花括号内。原输入已保留。'
      : '未保存：' + text + ' 原输入已保留。';
    message.hidden = false;
    if (!document.getElementById('submission').hidden) message.scrollIntoView({block: 'nearest'});
  };
  new MutationObserver(copyError).observe(original, {childList: true, characterData: true, subtree: true});
  document.getElementById('showSubmit').addEventListener('click', copyError);
  document.documentElement.dataset.submissionUiVersion = 'A-D07-submission-ui-v1';
})();
