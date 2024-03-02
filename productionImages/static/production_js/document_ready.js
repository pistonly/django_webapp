function searchProduct(){
    var $input = $("#production-input");
    var search_url = $("#search-batch-url").data("url");

    $input.autocomplete({
        source: function(request, response) {
            $.ajax({
                url: search_url,
                dataType: "json",
                data: { term: request.term },
                success: function(data) {
                    // Ensure the data is mapped to an array of objects with label and value
                    response($.map(data, function(item) {
                        return { label: item, value: item };
                    }));
                }
            });
        },
        select: function(event, ui) {
            getProductImages(ui.item.value);
        }
    });
}

$(document).ready(function() {
    getLatestProduct();
    searchProduct();
});
