
document.querySelectorAll('[data-group]').forEach(button => {
  const clips = [...document.getElementById(button.dataset.group).querySelectorAll('video')];
  const playing = () => clips.some(v => !v.paused && !v.ended);
  const update = () => {
    button.textContent = playing() ? 'Pause all three' : 'Replay all three';
  };
  for (const v of clips) {
    for (const event of ['play', 'pause', 'ended']) v.addEventListener(event, update);
  }
  button.addEventListener('click', () => {
    const pause = playing();
    for (const v of clips) {
      if (pause) v.pause(); else {v.currentTime=0;v.play().catch(()=>{});}
    }
    update();
  });
});
