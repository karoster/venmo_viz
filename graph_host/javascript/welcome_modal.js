let modal = document.getElementById("myModal");
// Get the <span> element that closes the modal
let closeSpan = document.querySelector(".close");

//install modal extension listeners
closeSpan.onclick = function() {
    modal.style.display = "none";
}

window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}