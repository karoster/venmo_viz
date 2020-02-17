map.addControl(new mapboxgl.NavigationControl());

    //fields that will get injected into/displayed on mouseover of transaction edges (when zoom >= 6)
let actorField = document.getElementById('actor');
let actionField = document.getElementById('action');
let targetField = document.getElementById('target');
let dateField = document.getElementById('date');
let messageField = document.getElementById('message');
let transactionDiv = document.querySelector('.transactionInfo');
let zoomField = document.getElementById('zoom');


let usernamePopup = null

map.on('load', () => {

    zoomField.textContent =  map.getZoom().toFixed(2);

    map.on('click', '1m-nodes (1)', function(e) {
        if(map.getZoom() >= 7){
            let url = `https://venmo.com/${e.features[0].properties.username}`;
            window.open(url, "_blank");
        }
    });

    //when mousing over node, display a popup showing username and change the cursor style
    map.on('mousemove', '1m-nodes (1)', function(e) {
        if(map.getZoom() >= 7){
            map.getCanvas().style.cursor = 'pointer';
            let username = e.features[0].properties.username;
            if(!username){username="Loading..."}
            let coordinates = e.features[0].geometry.coordinates.slice();

            if(!usernamePopup){
                usernamePopup = new mapboxgl.Popup({ closeOnClick: false })
                .setLngLat(coordinates)
                .setHTML(`<h4>${username}</h4>`)
                .addTo(map);
            } else if(usernamePopup._content.lastChild.textContent !=`${username}`) {
                usernamePopup.remove();
                usernamePopup = null;
            }
        }
    });

    //if leaving node delete the aforementioned popup
    map.on('mouseleave', '1m-nodes (1)', function(e){
        if(map.getZoom() >= 7){
            map.getCanvas().style.cursor = '';
            if(usernamePopup){
                usernamePopup.remove();
                usernamePopup = null;
            }
        }
    });

    //when hovering over edge populate text content fields of the transactionDiv
    map.on('mousemove', 'mod-1m', function(e) {

        if(map.getZoom() >= 6){
            let props = e.features[0].properties
            
            map.getCanvas().style.cursor = 'default';
            actorField.textContent = props.actor_name;
            actionField.textContent = props.action;
            targetField.textContent = props.target_name;
            dateField.textContent = props.date;
            messageField.textContent = props.message;
            transactionDiv.classList.remove('toggle-off');
            transactionDiv.classList.add('toggle-on');
        }
    });

    //when mouse leaves edge clean up the fields and hide it
    map.on('mouseleave', 'mod-1m', function(){
        transactionDiv.classList.remove('toggle-on');
        transactionDiv.classList.add('toggle-off');
        map.getCanvas().style.cursor = '';
        actorField.textContent = '';
        actionField.textContent = '';
        targetField.textContent = '';
        dateField.textContent = '';
        messageField.textContent = '';
    });

    //update the zoom tracker on bottom right corner
    map.on('zoomend', function(e){
        zoomField.textContent = map.getZoom().toFixed(2);
    });
});
