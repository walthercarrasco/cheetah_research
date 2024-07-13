setTimeout(function() {
    var messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        var alert = new bootstrap.Alert(message);
        alert.close();
            });
        }, 10000);