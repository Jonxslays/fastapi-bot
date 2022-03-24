const getError = () => {
    const page = window.location.pathname;
    if (!page.endsWith("oops")) return "";

    const message = window.location.search.slice(1);
    document.getElementById("error-message").appendChild(
        document.createElement("p").appendChild(
            document.createTextNode(decodeURI(message))
        )
    );
}
