(function($) {
    $(document).ready(function () {
        console.log('Auto Save ✅');

        $('.field-is_fast_shipping input, .field-status select').on('change', function () {
            console.log('Field Changed');
            
            var $row = $(this).closest('tr');
            var checkbox = $row.find('.action-checkbox');

            if (!checkbox.prop('checked')) {
                checkbox.prop('checked', true); // Force check row
            }

            // Append the "_save" action to the form (this is the secret 🔥)
            $('form#changelist-form').append('<input type="hidden" name="_save" value="1">');

            setTimeout(() => {
                $('form#changelist-form').submit();
            }, 300);
        });
    });
})(django.jQuery);
