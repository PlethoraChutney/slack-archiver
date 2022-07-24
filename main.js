const reactions = document.getElementsByClassName('react');
const hoverContainer = document.getElementById('mouseover-container');

for (let reaction of reactions) {
    reaction.addEventListener('mouseover', (event) => {

        let userArray = reaction.getAttribute('data-users').split(',');
        for (let user of userArray) {
            newUser = document.createElement('p');
            newUser.innerText = user.replace('_', ' ');
            hoverContainer.appendChild(newUser);
        }

        hoverContainer.style.top = event.pageY + 'px';
        hoverContainer.style.left = event.pageX + 'px';

        hoverContainer.classList.remove('hidden');
    })

    reaction.addEventListener('mouseleave', () => {
        while(hoverContainer.firstChild) {
            hoverContainer.removeChild(hoverContainer.firstChild);
        }
        hoverContainer.classList.add('hidden');
    })
}